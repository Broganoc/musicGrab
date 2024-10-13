import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, LEFT, CENTER
import requests
import os
from urllib.parse import urlparse
from urllib.request import urlretrieve
import webbrowser
import time

YOUTUBE_API_KEY = 'AIzaSyBYORpV8kJ_4FVf6sm_A709ENCjkc7DtlE'

class AppStyle:
    TITLE_FONT_SIZE = 18
    ITEM_FONT_SIZE = 16

    @staticmethod
    def input_style():
        return Pack(padding=10, font_size=14, flex=1)

    @staticmethod
    def button_style():
        return Pack(padding=10, font_size=14)

    @staticmethod
    def result_item_style(index):
        return Pack(direction=ROW, padding=10, alignment=CENTER, flex=1)

    @staticmethod
    def label_style(font_size):
        return Pack(padding=2, font_size=font_size, text_align='left')


class MusicGrab(toga.App):
    def startup(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        self.search_input = self.create_search_input()
        search_button = self.create_search_button()
        self.scroll_container = self.create_scroll_container()

        main_box.add(self.search_input)
        main_box.add(search_button)
        main_box.add(self.scroll_container)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def create_search_input(self):
        return toga.TextInput(placeholder="Enter your search...", style=AppStyle.input_style())

    def create_search_button(self):
        return toga.Button("Search", on_press=self.on_search, style=AppStyle.button_style())

    def create_scroll_container(self):
        self.results_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
        return toga.ScrollContainer(content=self.results_box, style=Pack(flex=1))

    def on_search(self, widget):
        query = self.search_input.value
        if query:
            results = self.fetch_info(query)
            self.display_results(results)

    def authenticate_spotify(self):
        client_id = 'c2ec9959815441548b32c086e9325132'
        client_secret = '58a48b0103fe41f6ad5af40f6dde2c09'
        token_url = 'https://accounts.spotify.com/api/token'

        response = requests.post(token_url, {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        })

        if response.status_code != 200:
            print("Could not authenticate with Spotify API.")
            return None

        return response.json().get('access_token')

    def fetch_info(self, query):
        self.access_token = self.authenticate_spotify()  # Store the token here
        if not self.access_token:
            return {}

        search_url = f"https://api.spotify.com/v1/search?q={query}&type=track,artist,album,playlist"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        search_response = requests.get(search_url, headers=headers)

        if search_response.status_code == 200:
            results = {
                'tracks': self.process_items(search_response.json().get('tracks', {}).get('items', []), 'track'),
                'artists': self.process_items(search_response.json().get('artists', {}).get('items', []), 'artist'),
                'albums': self.process_items(search_response.json().get('albums', {}).get('items', []), 'album'),
                'playlists': self.process_items(search_response.json().get('playlists', {}).get('items', []), 'playlist'),
            }
            return results
        else:
            print("Failed to retrieve data.")
            return {}

    def process_items(self, items, item_type):
        results = []
        for item in items:
            if item_type == 'track':
                # Omit BPM-related functionality
                results.append({
                    'type': item_type,
                    'name': item['name'],
                    'artist': ', '.join(artist['name'] for artist in item['artists']),
                    'popularity': item.get('popularity'),
                    'image_url': item['album']['images'][0]['url'] if item.get('album') and item['album'].get('images') else None,
                    'album': item['album']['name'] if item.get('album') else None
                })
            else:
                results.append({
                    'type': item_type,
                    'name': item['name'],
                    'id': item['id'],
                    'image_url': item['images'][0]['url'] if item.get('images') else None
                })
        return results

    def display_results(self, results):
        self.results_box.clear()  # Clear previous results

        for key, title in [('tracks', "Tracks"), ('artists', "Artists"), ('albums', "Albums"), ('playlists', "Playlists")]:
            if key in results:
                self.add_to_list(title, results[key], lambda item: item['name'])

    def add_to_list(self, title, items, format_func):
        title_label = toga.Label(title + ":", style=Pack(font_weight='bold', padding=5))
        self.results_box.add(title_label)

        for item in items:
            item_box = toga.Box(style=Pack(direction=ROW, padding=10, alignment=CENTER, flex=1))
            if 'image_url' in item and item['image_url']:
                image_file_name = self.download_image(item['image_url'])
                image = toga.ImageView(image_file_name, style=Pack(width=80, height=80))
                item_box.add(image)

            text_box = self.create_text_box(item, format_func(item))
            item_box.add(text_box)

            if item['type'] == 'track':
                search_button = toga.Button("Search YouTube", on_press=lambda w, item=item: self.search_youtube(item),
                                            style=AppStyle.button_style())
                item_box.add(search_button)
            elif item['type'] == 'artist':
                spotify_button = toga.Button("Show Albums", on_press=lambda w, item=item: self.show_albums(item),
                                             style=AppStyle.button_style())
                item_box.add(spotify_button)
            elif item['type'] == 'album':
                spotify_button = toga.Button("Search Spotify", on_press=lambda w, item=item: self.search_spotify(item),
                                             style=AppStyle.button_style())
                item_box.add(spotify_button)

            self.results_box.add(item_box)

    def show_albums(self, artist):
        access_token = self.authenticate_spotify()
        if not access_token:
            return

        search_url = f"https://api.spotify.com/v1/artists/{artist['id']}/albums"
        headers = {'Authorization': f'Bearer {access_token}'}
        albums_response = requests.get(search_url, headers=headers)

        if albums_response.status_code == 200:
            albums = albums_response.json().get('items', [])
            self.display_results({'albums': self.process_items(albums, 'album')})
        else:
            print("Failed to retrieve albums from Spotify API.")

    def search_spotify(self, item):
        if item['type'] == 'album':
            self.fetch_tracks(item['id'])

    def fetch_tracks(self, album_id):
        access_token = self.authenticate_spotify()
        if not access_token:
            return

        tracks_url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
        headers = {'Authorization': f'Bearer {access_token}'}
        tracks_response = requests.get(tracks_url, headers=headers)

        if tracks_response.status_code == 200:
            tracks = tracks_response.json().get('items', [])
            for track in tracks:
                track['artist'] = ', '.join(artist['name'] for artist in track['artists'])
            self.display_results({'tracks': self.process_items(tracks, 'track')})
        else:
            print("Failed to retrieve tracks from Spotify API.")

    def create_text_box(self, item, title_text):
        text_box = toga.Box(style=Pack(direction=COLUMN, padding_left=10, alignment=LEFT, flex=1))
        title_label = toga.Label(title_text, style=AppStyle.label_style(AppStyle.ITEM_FONT_SIZE))
        text_box.add(title_label)

        return text_box

    def search_youtube(self, item):
        if item['type'] == 'track':
            artist_name = item.get('artist', 'Unknown Artist')
            query = f"{item['name']} by {artist_name}"
        elif item['type'] == 'artist':
            query = item['name']
        elif item['type'] == 'album':
            query = f"{item['name']} album"
        else:
            return

        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=1&q={query}&key={YOUTUBE_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['items']:
                video_id = data['items'][0]['id'].get('videoId')
                if video_id:
                    webbrowser.open(f"https://www.youtube.com/watch?v={video_id}")
        else:
            print("Failed to retrieve data from YouTube API.")

    def download_image(self, url):
        parsed_url = urlparse(url)
        image_file_name = os.path.join(os.getcwd(), os.path.basename(parsed_url.path))

        if not os.path.exists(image_file_name):
            urlretrieve(url, image_file_name)

        return image_file_name


def main():
    return MusicGrab("Music Grab", "org.example.musicgrab")


if __name__ == '__main__':
    main().main_loop()
