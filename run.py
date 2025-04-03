from flask import Flask, redirect, request, session, render_template
import requests
from models import db

from models import Restaurant

app = Flask(__name__)
app.secret_key = "1274hd7gd13h2dG4ih26rd2733fg82hf8"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurants.db'
db.init_app(app)


APP_ID = "967570292026238"
APP_SECRET = "9523bc2e435818c1bfb15c514b0384c5"
REDIRECT_URI = "https://9033-116-199-207-98.ngrok-free.app/callback"


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
def index():
    return render_template("index.html")

@app.route("/getstarted", methods=['GET', 'POST'])
def getstarted():
    if request.method == 'POST':
        # Create restaurant in database immediately (without access token)
        restro_name = request.form.get('restro-name')
        print(restro_name)
        menu_items = [
            {'name': 'Cheeseburger', 'price': '$5'},
            {'name': 'Margherita Pizza', 'price': '$5'},
            {'name': 'Chicken Biryani', 'price': '$5'}
        ]
        item_names = [item['name'] for item in menu_items]
        
        new_restro = Restaurant(name=restro_name, items=item_names)
        db.session.add(new_restro)
        db.session.commit()
        
        # Store just the ID in session
        session['restro_id'] = new_restro.id
        session.modified = True
        
        # Redirect to Instagram auth
        auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&scope=instagram_basic,instagram_manage_insights,pages_show_list"
        return redirect(auth_url)
    
    return render_template('getstarted.html')    


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
            restaurant = Restaurant.query.get(1)
            restaurant.access_token=session["access_token"]
            db.session.commit()
            
            return redirect("/menus")
        else:
            return f"Error getting long-lived token: {long_token_data}", 400
    else:
        return f"Error getting access token: {data}", 400

@app.route("/menus")
def menus():
    restaurants = Restaurant.query.all()
    restaurant_data = []
    
    for restaurant in restaurants:
        # Ensure we're accessing the items attribute, not the items() method
        menu_items = restaurant.items if hasattr(restaurant, 'items') else []
        
        restaurant_data.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'menu_items': menu_items,  # Changed from 'items' to 'menu_items'
            'access_token': restaurant.access_token,
            'rating': 4.5
        })
    
    return render_template("menus.html", restaurants=restaurant_data)


@app.route("/menu")
def menu():
    # Get restaurant from database
    restaurant = Restaurant.query.get(1)
    if not restaurant:
        return "Restaurant not found", 404
    
    # Process menu items
    menu_items = []
    if restaurant.items:
        for item in restaurant.items:
            if isinstance(item, str):
                menu_items.append({'name': item, 'price': ''})
            elif isinstance(item, dict):
                menu_items.append({
                    'name': item.get('name', 'Unnamed Item'),
                    'price': item.get('price', '')
                })

    # Prepare restaurant data
    restaurant_data = {
        'id': restaurant.id,
        'name': restaurant.name,
        'menu_items': menu_items,
        'videos': []
    }

    # Get Instagram videos if access token exists
    if restaurant.access_token and restaurant.access_token != 'temporary_token':
        try:
            def get_instagram_posts(instagram_id, access_token):
                url = f"https://graph.facebook.com/v18.0/{instagram_id}/media"
                params = {
                    "fields": "id,media_url,permalink,media_type,timestamp,caption",
                    "access_token": access_token
                }
                response = requests.get(url, params=params)
                return response.json().get("data", [])

            # Get Instagram business account
            pages_url = "https://graph.facebook.com/v18.0/me/accounts"
            pages_response = requests.get(pages_url, params={"access_token": restaurant.access_token})
            pages_data = pages_response.json()

            if "data" in pages_data and pages_data["data"]:
                page_id = pages_data["data"][0]["id"]
                
                ig_url = f"https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account"
                ig_response = requests.get(ig_url, params={"access_token": restaurant.access_token})
                ig_data = ig_response.json()

                if "instagram_business_account" in ig_data:
                    instagram_id = ig_data["instagram_business_account"]["id"]
                    posts = get_instagram_posts(instagram_id, restaurant.access_token)
                    
                    # Filter for videos by checking .mp4 in media_url
                    for post in posts:
                        media_url = post.get('media_url', '')
                        if '.mp4' in media_url.lower():  # Check if media_url contains .mp4
                            restaurant_data['videos'].append({
                                'url': f"https://www.instagram.com/p/{post.get('id')}/embed",
                                'video_url': media_url,  # Direct MP4 URL
                                'thumbnail': media_url.replace('.mp4', '.jpg'),  # Assuming thumbnail exists
                                'caption': post.get('caption', '')
                            })
                            
        except Exception as e:
            print(f"Error fetching Instagram posts: {e}")        
    print(restaurant_data)
    return render_template("menu.html", restaurant=restaurant_data)

if __name__=="__main__":
    app.run(debug=True)