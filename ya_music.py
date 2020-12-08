from yandex_music.client import Client, Track
from config import ya_login, ya_password


class MyMusicClient:
    client = Client.from_credentials(ya_login, ya_password, report_new_fields=False)

    @staticmethod
    def get_track_fullname(track: Track):
        title = track.title
        artists = [artist.name for artist in track.artists]
        artists_str = ', '.join(artists)
        return f'{title} - {artists_str}'

    def search(self, query):
        found = self.client.search(query)
        found_tracks = found.tracks

        if found_tracks is None or found_tracks.total == 0:
            return [[], []]
        else:
            results = found_tracks.results
            ids = [i.id for i in results]

            if len(results) > 10:
                results = results[:10]

            return [self.get_options_from_tracks(results), ids]

    def get_options_from_tracks(self, tracks: list):
        options = [self.get_track_fullname(track)[:100] for track in tracks]  # poll options length must not exceed 100
        return options

    # {'full_lyrics': '...', 'videos': [...]}
    def get_supplement(self, track_id):
        info = self.client.track_supplement(track_id).to_dict()
        res = {'full_lyrics': None, 'videos': None}
        if info['lyrics'] is not None:
            if 'full_lyrics' in info['lyrics']:
                if info['lyrics']['full_lyrics'] is not None:
                    res['full_lyrics'] = info['lyrics']['full_lyrics']
        if info['videos'] is not None:
            if len(info['videos']) > 0:
                res['videos'] = [video for video in info['videos']]
        return res

    def get_similar(self, track_id):
        # Returns list of similar tracks, their ids
        similar_tracks = self.client.tracks_similar(track_id).similar_tracks

        # if there is no similar tracks or only one (minimum options in poll is 2)
        if len(similar_tracks) <= 1:
            return ['No similar tracks found', None]
        else:
            options = self.get_options_from_tracks(similar_tracks)
            similar_tracks_ids = [i.id for i in similar_tracks]

            return [options, similar_tracks_ids]

    def download_track(self, track_id, path):
        try:
            self.client.tracks([track_id])[0].download(path)
            return 'ok'
        except Exception as e:
            return f'Unexpected error occured:\n{e}\nTry again later.'


if __name__ == '__main__':
    client = MyMusicClient()
