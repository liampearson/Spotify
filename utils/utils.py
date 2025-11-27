import os 
import base64
from requests import post, get
import json
import glob #iterating over files
import pandas as pd
from dotenv import load_dotenv
# Load the environment variables from .env
load_dotenv()

#import API keys from .env file
client_id = os.environ.get("SPOTIFY_CLIENT_ID")
client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
#print(client_id, client_secret)
if not client_id:
    print("issue with client_id")
if not client_secret:
    print("issue with client_secret")


def import_streaming_data(parent_folder):

    #empty dataframe to collect batches
    _df = pd.DataFrame()
    
    #we'll get all the .json files like this
    file_name = "Streaming_History_Audio_*.json"
    
    #iterate over each .json file
    for file in glob.glob(parent_folder+file_name):
        print("reading in file:'{}'...".format(file))
        temp = pd.read_json(file)
        _df = pd.concat([_df, temp])

    #reset index
    _df.reset_index(drop=True, inplace=True)
    
    #drop columns that are not required in this analysis
    _df.drop(['ip_addr', 'platform'], axis=1, inplace=True)
    
    #rename columns so easier to read
    _df.rename(columns={'master_metadata_album_artist_name': 'artist',
                       'master_metadata_track_name': 'song',
                       'master_metadata_album_album_name': 'album'}, inplace=True)
    
    #based on earlier EDA, a null artist/song/album is because the record is a podcast
    _df[['artist', 'song', 'album']] = _df[['artist', 'song', 'album']].fillna('podcast')
    
    #order by timestamp
    _df.sort_values(by='ts', inplace=True)
    
    #see column names
    print("Columns:")
    print(_df.columns.values)
    
    #length and width of dataframe
    print("\nShape of Dataframe:")
    print(_df.shape)
    
    return _df



#Reference: https://www.youtube.com/watch?v=WAmEZBEeNmg
def get_token():
    """
    Take the client ID, concatenate it to our client secret and encode that with
    base 64 encoding (= authorisation string) and send to retrieve authorisation token
    """
    
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    #the url we want to send a request to
    url = "https://accounts.spotify.com/api/token"
    headers = {
    "Authorization": "Basic " + auth_base64, #send auth data and it'll verify it
    "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)

    #we'll get json data back; convert to json dictionary so can access "content" field
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

token=get_token()


def get_auth_header(token=token):
    """
    construct the header required when sending a request
    """
    return {"Authorization": "Bearer " + token}


def get_json_response(url, token=token):
    headers = get_auth_header(token)
    #attempt to get result from api
    try:
        result = get(url, headers=headers)
        json_result = json.loads(result.content)#["artists"]["items"]
    except:
        print("Error getting result from api")
        
    if len(json_result)==0:
        print("No Results for:{}".format(track_id))
        return None

    return json_result

def get_spotify_resource(spotify_id):
    try:
        # Try as a track
        url = "https://api.spotify.com/v1/tracks/{id}".format(id=spotify_id)
        return get_json_response(url)['type']
    except:
        pass #take no action if fails
    
    try:
        # Try as a artist
        url = "https://api.spotify.com/v1/artists/{id}".format(id=spotify_id)
        return get_json_response(url)['type']
    except:
        pass #take no action if fails
    
    try:
        # Try as an album
        url = "https://api.spotify.com/v1/albums/{id}".format(id=spotify_id)
        return get_json_response(url)['type']
    except:
        pass #take no action if fails

    try:
        # Try as a playlist
        url = "https://api.spotify.com/v1/playlists/{id}".format(id=spotify_id)
        return get_json_response(url)['type']
    except:
        pass #take no action if fails
    
    return "unknown"
    

def get_info(spotify_id, resource_type=""):
    """
    search for a song using the URI and get song info
    Fields of interest:
        popularity: 
    """  
    #Reference: https://developer.spotify.com/documentation/web-api/reference/search

    #if a URI was passed instead of an id, extract the resource type and if separately
    if spotify_id.split(":")[0]=="spotify":
        _, resource_type, spotify_id =spotify_id.split(":")

    #if a resource type was not passed, get it by querying API
    elif resource_type=="":
        resource_type = get_spotify_resource(spotify_id)

    url = "https://api.spotify.com/v1/{type}s/{id}".format(type=resource_type, id=spotify_id)

    json_result=get_json_response(url)
    
    return json_result
    

def get_album_image_url(spotify_id):
    try:
        json_result = get_info(spotify_id)
        return json_result['album']['images'][2]['url']
    except:
        print("Error getting album image")

def get_artist_image_url(spotify_id):
    try:
        json_result = get_info(spotify_id)
        return json_result['images'][2]['url']
    except:
        print("Error getting artist image")

def convert_track_uri_to_artist_uri(spotify_id):
    try:
        json_result = get_info(spotify_id)
        return json_result['artists'][0]['id']
    except:
        print("Error converting track_uri to artist_uri")

def display_images_in_dataframe(_df, image_link_col="image_url", scale=1):
    from IPython.display import HTML

    scale=str(scale*100)
    
    # Function to create HTML <img> tags
    def path_to_image_html(path):
        #return f'<img src="{path}">'  # Using alt attribute for fallback and setting height
        return f'<img src="{path}", width="{scale}%", height="{scale}%">'  # Using alt attribute for fallback and setting height
    
    _df['image'] = _df[image_link_col].apply(path_to_image_html)
    _df.drop(image_link_col, axis=1, inplace=True)
    
    # Display the DataFrame with images, ensuring the images render correctly
    return HTML(_df.to_html(escape=False, formatters={'Image': lambda x: x}))

def display_image_from_url(url):
    import requests
    from PIL import Image
    from io import BytesIO
    from IPython.display import display
    try:
        # Fetch the image content from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Open the image using Pillow
        img = Image.open(BytesIO(response.content))
        
        # Display the image
        display(img)
    except Exception as e:
        print(f"Error loading image: {e}")

def get_top_n_songs(_df, n=5):
    """
    Returns the top N most played songs with their artists, play counts, and album artwork URLs.

    Parameters:
    _df (pandas.DataFrame): DataFrame containing streaming history with 'artist', 'song', 'spotify_track_uri', and 'ts' columns.
    n (int, optional): Number of top songs to return. Default is 5.

    Returns:
    pandas.DataFrame: DataFrame indexed from 1 with columns 'artist', 'song', 'count', and 'image_url'.
    """
    
    #convert artist name to spotify URI
    artist_track_uri_map = _df.sort_values(by='ts', ascending=False).drop_duplicates(subset='artist', keep='first')[['artist', 'spotify_track_uri']]

    #some songs have multiple album artwork, so for each unique track we want the album artwork which
    #was played the most. Hence we get the top played URI per song by grouping-by URI and dropping duplicate artist/song pairs
    uri_consolidation = _df.groupby(['artist', 'song', 'spotify_track_uri']).size().reset_index(name='count').sort_values('count', ascending=False)
    uri_consolidation.drop_duplicates(['artist', 'song'], keep='first', inplace=True)
    uri_consolidation.drop('count', axis=1, inplace=True)
    
    #get vaue counts and take top n
    top_n_songs = pd.DataFrame(_df[['artist', 'song']].value_counts().head(n)).reset_index()
    #rename columns
    top_n_songs.columns = ['artist', 'song', 'count']
    #our data has the track's URI. Join this onto the top_5_artists
    top_n_songs = top_n_songs.merge(uri_consolidation, how='inner', on=['artist', 'song'])

    #get the artist's profile image
    top_n_songs['image_url'] = top_n_songs['spotify_track_uri'].apply(get_album_image_url)
    #no longer need these columns
    top_n_songs.drop(['spotify_track_uri'], axis=1, inplace=True)
    
    # Reset the index and make it start from 1
    top_n_songs = top_n_songs.reset_index(drop=True)  # Reset index, dropping the old one
    top_n_songs.index = top_n_songs.index + 1        # Shift index by 1
    return top_n_songs
    

def get_top_n_artists(_df, n=5):
    """
    Returns the top N most played artists with their play counts and profile image URLs.

    Parameters:
    _df (pandas.DataFrame): DataFrame containing streaming history with 'artist', 'spotify_track_uri', and 'ts' columns.
    n (int, optional): Number of top artists to return. Default is 5.

    Returns:
    pandas.DataFrame: DataFrame indexed from 1 with columns 'artist', 'count', and 'image_url'.
    """
    
    #convert artist name to spotify URI
    artist_track_uri_map = _df.sort_values(by='ts', ascending=False).drop_duplicates(subset='artist', keep='first')[['artist', 'spotify_track_uri']]

    #get vaue counts and take top n
    top_n_artists = pd.DataFrame(_df['artist'].value_counts().head(n)).reset_index()
    #rename columns
    top_n_artists.columns = ['artist', 'count']
    #our data has the track's URI. Join this onto the top_5_artists
    top_n_artists = top_n_artists.merge(artist_track_uri_map, how='inner', on='artist')
    #convert the track URI to an artist URI
    top_n_artists['spotify_artist_uri'] = top_n_artists['spotify_track_uri'].apply(convert_track_uri_to_artist_uri)
    #get the artist's profile image
    top_n_artists['image_url'] = top_n_artists['spotify_artist_uri'].apply(get_artist_image_url)
    #no longer need these columns
    top_n_artists.drop(['spotify_track_uri', 'spotify_artist_uri'], axis=1, inplace=True)
    
    # Reset the index and make it start from 1
    top_n_artists = top_n_artists.reset_index(drop=True)  # Reset index, dropping the old one
    top_n_artists.index = top_n_artists.index + 1        # Shift index by 1
    return top_n_artists