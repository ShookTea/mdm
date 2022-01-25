#!/usr/local/bin/python3

from posixpath import dirname
from types import AsyncGeneratorType
import urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Iterator, List
from locale import atof
from hashlib import md5
import os, re

url = 'https://www.mdm.pl/ui-pub/site/analizy_i_rynek/analizy_i_rekomendacje/analiza_fundamentalna/rekomendacje'
dir_path = os.path.dirname(os.path.realpath(__file__))
file = dir_path + "/recommendations.md"

@dataclass
class Recommendation:
    company: str
    date: str
    priceOnPublication: float
    estimation: float

    def getIncrementationPercentage(self) -> float:
        return self.estimation / self.priceOnPublication - 1.0

    def __str__(self) -> str:
        return "[{0}] {1} ({2:.2f} ---({3:.2%})---> {4:.2f})".format(
            self.date, self.company, self.priceOnPublication, self.getIncrementationPercentage(), self.estimation
        )
    
    def toMarkdown(self) -> str:
        return "{} | {} | {} | {:.2f} | {:.2%} | {:.2f}".format(
            self.hash(),
            self.date,
            self.company,
            self.priceOnPublication,
            self.getIncrementationPercentage(),
            self.estimation
        )

    def hash(self) -> str:
        return md5(self.__str__().encode()).hexdigest()[0:4]

@dataclass
class RecommendationFile:
    recommendations: List[Recommendation]
    date: str

    def add(self, r: Recommendation):
        append = True
        for index, entry in enumerate(self.recommendations):
            if entry.company == r.company and entry.date == r.date:
                if entry.hash() != r.hash():
                    self.recommendations[index] = r
                append = False
                break
        if append:
            self.recommendations.append(r)
        self.recommendations.sort(key=lambda x: x.date, reverse=True)
        self.date = self.recommendations[0].date

    def toMarkdown(self) -> str:
        dateHeader = "# " + self.date
        tableHeader = "checksum | data | spółka | cena początkowa | zmiana | cena końcowa"
        tableBorder = "---|---|---|---|---|---"
        result = dateHeader + "\n" + tableHeader + "\n" + tableBorder + "\n"
        for entry in self.recommendations:
            result = result + entry.toMarkdown() + "\n"
        return result

    def __hashBase(self) -> str:
        result = ""
        for entry in self.recommendations:
            result = result + entry.hash()
        return result

    def hash(self) -> str:
        return md5(self.__hashBase().encode()).hexdigest()[0:4]


def loadCurrentRecommendations() -> Iterator[Recommendation]:
    response = urllib.request.urlopen(url)
    webContent = response.read()
    soup = BeautifulSoup(webContent, features="html.parser")
    for row in soup.find('table', {'class': 'content-rekomendacja'}).find('tbody').find_all('tr'):
        cells = row.find_all('td')
        cellText = []
        for cell in cells:
            cellText.append(cell.text.strip())
        company, _, date, priceOnPublication, _, estimation, *_ = cellText
        if not re.match("^([0-9,.]+)$", estimation):
            continue
        yield Recommendation(company, date, atof(priceOnPublication), atof(estimation))

def readRecommendationFile():
    if not os.path.isfile(file):
        return RecommendationFile([], "0000-00-00")
    f = open(file, "r")
    dateRow = f.readline()[2:12]
    _ = f.readline()
    _ = f.readline()
    recommendations = []
    for line in f:
        _, date, company, startPrice, _, endPrice = line.split("|")
        recommendations.append(Recommendation(
            company.strip(),
            date.strip(),
            atof(startPrice.strip()),
            atof(endPrice.strip())
        ))
    f.close()
    return RecommendationFile(recommendations, dateRow)


recFile = readRecommendationFile()
for newEntry in loadCurrentRecommendations():
    recFile.add(newEntry)

f = open(file, "w")
f.write(recFile.toMarkdown())
f.close()
