import sys
import re
import urllib3
import os.path as p
from pathlib import Path
from bs4 import BeautifulSoup


class PythonVersionDownloader:
    """
    Class for parsing https://www.python.org and downloading concrete version of Python
    """
    __chunk_size = 1024
    __url = 'https://www.python.org/ftp/python/'
    
    @staticmethod
    def __check_desired_value(desired_version: str):
        if desired_version and not desired_version.replace('.', '').isdigit():
            raise ValueError(f'Incorrect format of desired value. Expected "#.#[.#]". Get {desired_version}')

    @staticmethod
    def __print_progress_bar(i, total, prefix='', suffix='', length=100, fill='█'):
        cur_bytes = i * PythonVersionDownloader.__chunk_size
        cur_percent = round(cur_bytes/total, 3)
        normalized_cur_bytes = length * cur_percent
        bar = fill*int(normalized_cur_bytes) + '-' * int(length - normalized_cur_bytes)
        print(f'\r{prefix} |{bar}| {round(cur_percent*100, 2)}% {i}/{int(total/1024)} KB {suffix}', end='\r')
        if i * PythonVersionDownloader.__chunk_size == total:
            print()
    
    def __init__(self, pool_num: int = 3):
        self.clear_version, self.version, self.data, self.path = None, None, None, Path(p.dirname(p.realpath(__file__)))
        self.http = urllib3.PoolManager(num_pools=pool_num)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __get_data(self):
        data = self.http.request('GET', PythonVersionDownloader.__url, preload_content=False)
        soup = BeautifulSoup(data.data, 'html.parser')
        self.data = soup.find_all('a', href=True)

    def __parse_version(self):
        values = list(filter(lambda html_tag: html_tag.isdigit(),
                             map(lambda html_tag: html_tag.string.replace('.', '', 2)[:-1], self.data)))
        if self.version:
            result = self.version if self.version in values else ''
        else:
            result = max(values)
        return '.'.join(result)

    def __file_download(self, search_url: str):
        print('Downloading: ', search_url)
        print('Location: ', self.path)
        r = self.http.request('GET', search_url, preload_content=False)
        total_size = int(r.info()['Content-Length'])
        with open(self.path.joinpath(f'python-{self.version}.exe'), 'wb') as f:
            counter = 0
            PythonVersionDownloader.__print_progress_bar(0, total_size, prefix='Progress:', length=50)
            while True:
                data = r.read(PythonVersionDownloader.__chunk_size)
                if not data:
                    break
                f.write(data)
                PythonVersionDownloader.__print_progress_bar(counter, total_size, prefix='Progress:', length=50)
                counter += 1
        r.release_conn()

    def download(self, path: str = None, version: str = None):
        PythonVersionDownloader.__check_desired_value(version)
        try:
            if path:
                self.path = Path(path)
            if not self.path.exists() or self.path.is_file():
                raise ValueError()
        except Exception:
            raise ValueError('Path is incorrect')
        self.clear_version = version
        self.version = version.replace('.', '') if version else ''
        self.__get_data()
        self.version = self.__parse_version()
        if self.clear_version and self.version != self.clear_version:
            raise Exception(f'Version {self.clear_version} not found')
        PythonVersionDownloader.__url += f'{self.version}/'
        self.__get_executable()

    def __get_executable(self):
        search_version = f'python-{self.version}.exe'
        search_url = PythonVersionDownloader.__url + search_version
        self.__get_data()
        r = self.http.request('HEAD', search_url)
        if r.status == 200:
            self.__file_download(search_url)
        elif r.status == 404:
            if input(f'Release versions {self.version} not found, do you want check beta and alpha versions? (y/n)\n') != 'n':
                self.__check_alpha_beta()

    def __check_alpha_beta(self):
        res = sorted(filter(lambda v: re.match(rf'^python-{self.version}[ab]\d+\.exe$', v.string), self.data),
                     key=lambda v: v.string, reverse=True)
        if res:
            res = res[0]
            self.version = re.search(rf'{self.version}[ab]\d+', res.string).group()
            self.__file_download(self.__url + '/' + res.string)
        else:
            raise ValueError('No versions not found')


def main():
    try:
        downloader = PythonVersionDownloader()
        if sys.argv:
            downloader.download(*sys.argv[1:])
        else:
            downloader.download()
    except Exception as err:
        print(err)
        print('\nInstructions:')
        print('Expected 2 optional arguments: download path, version of python in format #.#(.#)',
              'Default values of arguments: path of script, last available version of python')


if __name__ == '__main__':
    main()

