import json
import requests
import datetime


class MovieAPI:
    base_url = 'https://api.themoviedb.org/3'
    image_base_url = None
    api_key = None

    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get(
            self.base_url + '/configuration?api_key=' + self.api_key)
        self.image_base_url = response.json()['images']['base_url']

    def createQueryParams(self, **kwargs):
        query = '?api_key=' + self.api_key
        for key, value in kwargs.items():
            if value != None:
                query += '&' + key + '=' + value
        return query

    def getMovie(self, movie_id, **kwargs) -> json:
        url = self.base_url + '/movie/' + \
            str(movie_id) + self.createQueryParams(**kwargs)
        response = requests.get(url)
        return response.json()

    def getUpcomingMovies(self, **kwargs) -> json:
        # get upcoming movies within the next 3 weeks
        url = self.base_url + '/movie/upcoming' + self.createQueryParams(**kwargs) + '&primary_release_date.gte=' + datetime.datetime.now().strftime("%Y-%m-%d") + '&primary_release_date.lte=' + (datetime.datetime.now() + datetime.timedelta(days=21)).strftime("%Y-%m-%d")
        
        response = requests.get(url)
        return response.json()

    def searchMovie(self, query, **kwargs) -> json:
        url = self.base_url + '/search/movie' + \
            self.createQueryParams(**kwargs) + '&query=' + query
        response = requests.get(url)
        return response.json()
