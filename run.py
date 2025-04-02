from flask import Flask, redirect, request, session, render_template
import requests

app = Flask(__name__)
app.secret_key = "1274hd7gd13h2dG4ih26rd2733fg82hf8"

APP_ID = "967570292026238"
APP_SECRET = "9523bc2e435818c1bfb15c514b0384c5"
REDIRECT_URI = "https://d1c0-116-199-206-56.ngrok-free.app/callback"

# Helper function to fetch data
def fetch_data(url, params):
    response = requests.get(url, params=params)
    return response.json()

# Function to get Instagram posts (without comments)
def get_instagram_posts(instagram_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{instagram_id}/media"
    params = {
        "fields": "id,like_count,media_url,caption,media_type,children",
        "access_token": access_token
    }
    data = fetch_data(url, params)

    posts = []
    for post in data.get("data", []):
        post_data = {
            "id": post.get("id"),
            "media_url": post.get("media_url") if post.get("media_type") != "CAROUSEL_ALBUM" else None,
            "caption": post.get("caption"),
            "like_count": post.get("like_count"),
            "carousel_media": []
        }

        if post.get("media_type") == "CAROUSEL_ALBUM" and "children" in post:
            children_ids = post["children"]["data"]
            for child in children_ids:
                child_data = fetch_data(f"https://graph.facebook.com/v18.0/{child['id']}", 
                                      {"fields": "media_url", "access_token": access_token})
                if "media_url" in child_data:
                    post_data["carousel_media"].append(child_data["media_url"])

        posts.append(post_data)

    return posts

@app.route("/")
def home():
    auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&scope=instagram_basic,instagram_manage_insights,pages_show_list"
    return f'<a href="{auth_url}">Login with Instagram</a>'

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: Authorization code not received", 400
    
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    
    response = requests.get(token_url, params=params)
    data = response.json()

    if "access_token" in data:
        short_lived_token = data["access_token"]
        long_token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        long_token_params = {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_lived_token
        }

        long_response = requests.get(long_token_url, params=long_token_params)
        long_token_data = long_response.json()

        if "access_token" in long_token_data:
            session["access_token"] = long_token_data["access_token"]
            return redirect("/profile")
        else:
            return f"Error getting long-lived token: {long_token_data}", 400
    else:
        return f"Error getting access token: {data}", 400

@app.route("/profile")
def profile():
    access_token = session.get("access_token")
    if not access_token:
        return redirect("/")

    pages_url = "https://graph.facebook.com/v18.0/me/accounts"
    pages_params = {"access_token": access_token}
    pages_response = requests.get(pages_url, params=pages_params)
    pages_data = pages_response.json()

    if "data" in pages_data and len(pages_data["data"]) > 0:
        page_id = pages_data["data"][0]["id"]

        ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account"
        ig_params = {"access_token": access_token}
        ig_response = requests.get(ig_url, params=ig_params)
        ig_data = ig_response.json()

        if "instagram_business_account" in ig_data:
            instagram_id = ig_data["instagram_business_account"]["id"]

            insta_url = f"https://graph.facebook.com/v18.0/{instagram_id}"
            insta_params = {
                "fields": "id,username,followers_count,media_count",
                "access_token": access_token
            }
            insta_response = requests.get(insta_url, params=insta_params)
            insta_data = insta_response.json()
            
            # Get Instagram posts
            posts = get_instagram_posts(instagram_id, access_token)

            return render_template("index.html",
                                username=insta_data.get("username"),
                                followers_count=insta_data.get("followers_count"),
                                media_count=insta_data.get("media_count"),
                                posts=posts)

    return "Instagram Business Account not found or not connected.", 400

if __name__ == "__main__":
    app.run(debug=True)