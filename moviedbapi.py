import json
import requests
import datetime


class MovieAPI:
    base_url = 'https://api.themoviedb.org/3'
    image_base_url = None
    api_key = None
    languages: json = None
    countries: json = None
    genres: json = None

    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get(
            self.base_url + '/configuration' + self.createQueryParams())
        self.image_base_url = response.json()['images']['secure_base_url']
        self.languages = self.getLanguages()
        self.languages = list(filter(lambda x: '?' not in x["english_name"] and x["english_name"] != "No Language" and x["english_name"] != "", self.languages))
        self.languages.sort(key=lambda x: x["english_name"])
        self.countries = self.getCountries()
        self.countries.sort(key=lambda x: x["english_name"])
        self.genres = self.getGenres()

    def createQueryParams(self, **kwargs):
        query = '?api_key=' + self.api_key
        for key, value in kwargs.items():
            if value != None:
                query += '&' + key + '=' + value
        return query

    def getMovie(self, movie_id, **kwargs) -> json:
        url = self.base_url + '/movie/' + \
            str(movie_id) + self.createQueryParams(**kwargs)
        return requests.get(url).json()

    def getUpcomingMovies(self, **kwargs) -> json:
        # get upcoming movies within the next 3 weeks
        url = self.base_url + '/movie/upcoming' + self.createQueryParams(**kwargs) + '&primary_release_date.gte=' + datetime.datetime.now().strftime("%Y-%m-%d") + '&primary_release_date.lte=' + (datetime.datetime.now() + datetime.timedelta(days=21)).strftime("%Y-%m-%d")
        
        return requests.get(url).json()

    def getNowPlayingMovies(self, **kwargs) -> json:
        url = self.base_url + '/movie/now_playing' + self.createQueryParams(**kwargs)
        return requests.get(url).json()

    def searchMovie(self, query, **kwargs) -> json:
        url = self.base_url + '/search/movie' + \
            self.createQueryParams(**kwargs) + '&query=' + query
        return requests.get(url).json()

    def getCountries(self) -> json:
        url = self.base_url + '/configuration/countries' + \
            self.createQueryParams()
        return requests.get(url).json()   

    def getLanguages(self) -> json:
        url = self.base_url + '/configuration/languages' + \
            self.createQueryParams()
        return requests.get(url).json()

    def getGenres(self) -> json:
        url = self.base_url + '/genre/movie/list' + \
            self.createQueryParams()
        return requests.get(url).json().get('genres')

    def search(self, query, **kwargs) -> json:
        url = self.base_url + '/search/movie' + \
            self.createQueryParams(**kwargs) + '&query=' + query
        return requests.get(url).json()