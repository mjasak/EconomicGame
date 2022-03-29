import bs4 as bs
import urllib.request
import csv
import math
import os
import numpy as np
import matplotlib.pyplot as plt

'''
Na początku każdy gracz otrzymuje tą samą kwotę w PLN. 
--> Zlecenia:
 'Każdy gracz może złożyć wiele różnych ofert sprzedaży/kupna papierów każdego dnia 
 'Każdy gracz może sprzedać tylko te papiery, które posiada i w takiej liczbie jaką posiada.
 'Sumaryczna wartość ofert kupna nie może przekraczać stanu konta gotówkowego.
 'Przedmiotem obrotu są akcje z MIDWIG

 --> Giełda:
	Oferta sprzedaży (papier, ilość) zostanie zrealizowana, jeśli tego dnia na giełdzie:
 		(a) cena maksymalna jest niższa od ceny oferty
		(b) suma ilości we wszystkich zleceniach na ten papier jest mniejsza od 50% wolumenu obrotu 
		(c) jeśli warunek (b) nie jest spełniony to następuje proporcjonalna redukcja zleceń na ten papier 

	Oferta kupna (papier, ilość) zostanie zrealizowana, jeśli tego dnia na giełdzie: 
		(a) cena oferty kupna jest wyższa od ceny minimalnej.
		(b) suma ilości we wszystkich zleceniach na ten papier jest mniejsza od 50% wolumenu obrotu 
		(c) jeśli warunek (b) nie jest spełniony to następuje proporcjonalna redukcja zleceń na ten papier \

Wszystkie zlecenia są realizowane jednocześnie. Wynikiem gracza jest stan jego konta gotówkowego w dniu zakończenia gry.
Parametrami gry są daty jej rozpoczęcia i zakończenia. Dane z giełdy są dostępne na stronie https://www.gpw.pl/statystyki-gpw 
				
Aplikacja ma pozwalać na: 
		(1) składanie zleceń 
		(2) realizację zleceń 
		(3) odczytywane stanu konta 
		(4) prezentację wyników końcowych. 

Bonusami mogą być: 
(a) interfejs graficzny 
(b) graficzna prezentacja wyników 
c) wykorzystanie notowań ciągłych
'''


class Game:

    class Gamer:

        def __init__(self,name, mwig_dic, money = 100_000.0,):
            self.papers_stock_buy = dict.fromkeys(mwig_dic.keys(), [[0] * 2])
            self.papers_stock_sell = dict.fromkeys(mwig_dic.keys(), [[0] * 2])
            self.papers_possessed = dict.fromkeys(mwig_dic.keys(), 0)
            self.money = money
            self.money_res = 0
            self.name = name
            self.history = []


        def add_papers_toBuy(self, id, number, price):
            if self.papers_stock_buy[id][0][0] == 0:
                self.papers_stock_buy[id] = [[number, price]]
            else:
                self.papers_stock_buy[id].append([number, price])

        def add_papers_toSell(self, id, number, price):
            if self.papers_stock_sell[id][0][0] == 0:
                self.papers_stock_sell[id] = [[number, price]]
            else:
                self.papers_stock_sell[id].append([number, price])

        def remove_papers_bought(self, id, ix):
            if ix == 0 and self.papers_stock_buy[id][ix][0] == 0:
                return
            elif ix == 0:
                self.papers_stock_buy[id][ix] = [0, 0]
            else:
                self.papers_stock_buy[id].pop(ix)

        def remove_papers_sold(self, id, ix):
            if ix == 0 and self.papers_stock_sell[id][ix][0] == 0:
                return
            elif ix == 0:
                self.papers_stock_sell[id][ix] = [0, 0]
            else:
                self.papers_stock_sell[id].pop(ix)

        def score(self):
            return self.money

    class Stock:

        def __init__(self,mwig_dic):
            self.buy_count = dict.fromkeys(mwig_dic.keys(), 0)
            self.sell_count = dict.fromkeys(mwig_dic.keys(), 0)

        def round_tick(self, gamers, mwig):
            self.__init__(mwig)
            # petla sumujaca ilosc zlecen kazdego gracza dla danej spolki
            if gamers and mwig is not None:
                self.count_papers(gamers,mwig)
                # wykonanie wpierw akcji sprzedazy a pozniej kupna
                for g in gamers:
                    for k in mwig.keys():
                        if g.papers_stock_sell[k][0][0] != 0:
                            for s, ix in zip(g.papers_stock_sell[k], range(len(g.papers_stock_sell[k]))):
                                self.sell_offer(g,s, mwig[k], k)
                                g.remove_papers_sold(k, ix)

                    for k in mwig.keys():
                        if g.papers_stock_buy[k][0][0] != 0:
                            for b, ix in zip(g.papers_stock_buy[k], range(len(g.papers_stock_buy[k]))):
                                self.buy_offer(g,b, mwig[k], k)
                                g.remove_papers_bought(k, ix)

                    g.history.append(g.score())

        def count_papers(self,gamers,mwig):
            for g in gamers:
                for k in mwig.keys():
                    if g.papers_stock_buy[k][0][0] != 0:
                        for b in g.papers_stock_buy[k]:
                            self.buy_count[k] += b[0]
                    if g.papers_stock_sell[k][0][0] != 0:
                        for s in g.papers_stock_sell[k]:
                            self.sell_count[k] += s[0]

        def sell(self,key,gamer,order_count,price):
            # dodajemy do pieniedzy gracza sume ze sprzedanych papierow
            # sprzedane usuwamy z posiadanych papierow
            gamer.money += order_count * price
            gamer.papers_possessed[key] -= order_count

        def sell_offer(self,gamer,sell_offer, mwig1, key):
            # jesli proponowane cena jest nizsza od ceny maksymalnej sprzedajemy
            # jest polowa wolumenu jest przekroczona to sprzedaz zmniejszamy proporcjonalnie
            if sell_offer[1] < mwig1[0]:
                if self.sell_count[key] < mwig1[2]/2:
                    # sell
                    self.sell(key,gamer,sell_offer[0],sell_offer[1])
                else:
                    # ilosc papierow jest odpowiednio zmniejszona
                    temp = sell_offer[0] * mwig1[2]/2/self.sell_count[key]
                    self.sell(key,gamer,int(math.floor(temp)),sell_offer[1])

        # metody na kupno sa analogiczne do sprzedazowych z ograniczeniem na posiadane pienionzki
        def buy(self,key,gamer,order_count,price):
            if gamer.money >= order_count * price:
                gamer.money -= order_count * price
                gamer.papers_possessed[key] += order_count
                print(f"[{gamer.name}] Dokonano zakupu {order_count} akcji {key} po cenie {price}")
            else:
                print("Za malo srodkow na koncie")

        def buy_offer(self, gamer, buy_offer, mwig1, key):
            if buy_offer[1] > mwig1[1]:
                if self.buy_count[key] < mwig1[2]/2:
                    # buy
                    self.buy(key,gamer,buy_offer[0],buy_offer[1])
                else:
                    # ilosc papierow jest odpowiednio zmniejszona
                    temp = buy_offer[0] * mwig1[2]/2/self.buy_count[key]
                    self.buy(key,gamer,int(math.floor(temp)),buy_offer[1])

    class StockData:

        def __init__(self):
            self.path = 'mwig40.csv'

        def import_from_web(self):

            # sauce code
            if not os.path.exists(self.path):
                sauce = urllib.request.urlopen('https://stooq.pl/t/?i=533&v=1').read()
                soup = bs.BeautifulSoup(sauce, 'html.parser')
                table = soup.find('table', attrs={'class': 'fth1'})
                rows = table.find_all('tr')

                tbr = [['Symbol', 'Nazwa', 'Otwarcie', 'Max', 'Min', 'Kurs', 'Zmiana', 'Wolumen', 'Obrót', 'Data']]

                for r in rows:
                    data = r.find_all('td')
                    # sprawdz czy kolumny posiadaja dane
                    if len(data) == 0:
                        continue

                    # pisz zawartosc kolumny do zmiennej
                    symbol = data[0].getText()
                    nazwa = data[1].getText()
                    otwarcie = data[2].getText()
                    max = data[3].getText()
                    min = data[4].getText()
                    kurs = data[5].getText()
                    zmiana = data[6].getText()
                    wolumen = data[7].getText()
                    obrot = data[8].getText()
                    data = data[9].getText()

                    # dolacz wynik do wiersza
                    tbr.append([symbol, nazwa, otwarcie, max, min, kurs, zmiana, wolumen, obrot, data])

                    # Tworzy plik csv i zapisuje wiersze do pliku wyjsciowego
                    with open(self.path, 'w', newline='') as file:
                        csv_output = csv.writer(file)
                        csv_output.writerows(tbr)

        def read_from_csv(self):

            # Tworzy slownik o strukturze: symbol spolki(klucz) : [kurs max, kurs min, wolumen]
            mwig40_dic = {}
            stock_data = {}
            with open('mwig40.csv', 'r') as file:
                csvfile = csv.reader(file, delimiter=',')
                csvfile.__next__()
                for row in csvfile:
                    mwig40_dic[row[0]] = [float(row[3]), float(row[4]), row[7]]
                    stock_data[row[0]] = [float(row[3]), float(row[4]), row[7]]

            for i in mwig40_dic:
                if mwig40_dic[i][2][-1] == 'k':
                    mwig40_dic[i][2] = int(round(float(mwig40_dic[i][2][:-1]) * 1_000, -1))

                elif mwig40_dic[i][2][-1] == 'm':
                    mwig40_dic[i][2] = int(round(float(mwig40_dic[i][2][:-1]) * 1_000_000, -3))
                else:
                    pass
            return mwig40_dic,stock_data

    date_start = 0
    date_end = 0
    mwig40_dic = {}   # mwig o strukturze: symbol spolki(klucz) : [kurs max, kurs min, wolumen]
    stock_data = {}   # stockdata o strukturze: symbol spolki(klucz) : [kurs max, kurs min, wolumen [w tysiacach]]

    def __init__(self):

        self.StockData().import_from_web()
        self.mwig40_dic, self.stock_data = self.StockData().read_from_csv()

    def play_game(self):
        self.game_start()

        while self.date_start != self.date_end:
            self.game_round(self.mwig40_dic)
            self.date_start += 1

        winner, ix = self.gamers[0].money, 0
        for i in range(len(self.gamers)):
            if self.gamers[i].money > winner:
                winner = self.gamers[i].money
                ix = i

        print('\n *** Gra skonczyla sie! ***')
        print('\nWyniki graczy:')
        for g,ix in zip(self.gamers, range(len(self.gamers))):
            print(f"Gracz {ix+1} zakończył grę z wynikiem {g.score()}.")
            print("Historia", g.history)

        l = len(self.gamers)
        x = range(len(self.gamers[0].history))
        ax = tuple([None for _ in range(l)])
        print('\n *** Zwyciezca jest gracz {} ze stanem konta: {} ***\n'.format(self.gamers[ix].name, winner))
        print("Dziekujemy za rozgrywke.")
        print('Milego dnia.')

        plot = input("Czy narysowac przebieg gry? T/N : ")

        if l > 1 and plot.upper() == "T":
            fig, ax = plt.subplots(len(self.gamers))
            fig.suptitle('Przebieg gry')
            for g, i in zip(self.gamers, range(l)):
                ax[i].plot(x, g.history, 'o-')
                ax[i].set_ylabel(f"Wynik gracza {g.name}")
                if i == l - 1:
                    ax[i].set_xlabel("Dzien")
            plt.show()
        elif plot.upper() == 'T':
            plt.plot(x,self.gamers[0].history,'o-')
            plt.xlabel("Dzien")
            plt.ylabel(f"Wynik gracza {self.gamers[0].name}")
            plt.show()

    def game_start(self):

        print('Witaj w grze symulujacej podstawy dzialania gieldy!')
        while True:
            n_gamers = input('Liczba graczy bioracych udzial w grze: ')
            if n_gamers.isnumeric():
                n_gamers = int(n_gamers)
                break
        while True:
            init_amount = input('Poczatkowa suma pieniedzy na koncie kazdego gracza: ')
            if init_amount.isnumeric():
                init_amount = int(init_amount)
                break

        while True:
            rounds = input('Liczba rund do rozegrania: ')
            if rounds.isnumeric():
                rounds = int(rounds)
                break

        self.date_end = rounds

        self.gamers = [None] * n_gamers

        for i in range(n_gamers):
            imie = input(f"Podaj nazwe gracza {i+1}: ")
            # imie = "Gracz " + str(i+1)
            self.gamers[i] = self.Gamer(imie,self.mwig40_dic,init_amount)

    def game_round(self,mwig):

        print("\n","\t-------------------------\t","\n")
        print('Dzien {} wlasnie sie rozpoczyna!'.format(self.date_start+1))
        iteration = 0
        for g in self.gamers:
            self.gamer_move(g, iteration)
            iteration += 1
        print("\n --- ROUND LOG --- ")
        self.Stock(mwig).round_tick(self.gamers, mwig)

    def gamer_move(self, g, i):
        print('\n Graczu '+ str(i+1) + ' posiadasz: ' + str(g.money) + ' PLN! \n Co chcesz zrobic? [MENU]')
        print('(1) - Wyswietl kursy gieldowe spolek! \n(2) - Wyswietl posiadane papiery i stan konta \n\
(3) - Zloz oferte kupna \n(4) - Zloz oferte sprzedazy \n(9) - Wyswietl menu \n(0) - zakoncz swoja ture\n')

        move = input('Akcja gracza {}: '.format(i+1))
        while move:
            if move == '0':
                break

            elif move == '1':
                self.print_stock_data()

            elif move == '2':
                self.gamer_papers(g)
                print('Stan konta: {}'.format(g.money))

            elif move == '3':
                sym = input('Podaj symbol spolki: ')
                sym = sym.upper()
                if sym not in self.mwig40_dic.keys():
                    print('Niepoprawny symbol')

                else:
                    number = input('Podaj liczbe papierow do kupna: ')
                    price = input('Podaj cene kupna: ')

                    if number.isnumeric() and price.isnumeric():
                        self.gamer_buy(g, sym, int(number),float(price))
                    else:
                        print("Niepoprawna ilosc lub cena")

            elif move == '4':
                sym = input('Podaj symbol spolki: ')
                sym = sym.upper()
                if sym not in self.mwig40_dic.keys():
                    print('Niepoprawny symbol')
                else:
                    number = input('Podaj liczbe papierow do sprzedania: ')
                    price = input('Podaj cene sprzedazy: ')
                    if number.isnumeric() and price.isnumeric():
                        self.gamer_sell(g, sym, int(number),float(price))
                    else:
                        print("Niepoprawna ilosc lub cena")

            elif move == '9':
                print('(1) - Wyswietl kursy gieldowe spolek! \n(2) - Wyswietl posiadane papiery i stan konta \n \
                        (3) - Zloz oferte kupna \n(4) - Zloz oferte sprzedazy \n(9) - Wyswietl menu \n(0) - zakoncz swoja ture')

            else:
                print('Niepoprawna akcja')

            move = input('Akcja gracza: ')  #aktualizajca ruchu gracza

    def print_stock_data(self):
        print('\nSymbol' + ' Max' + ' Min' + ' Wolumen')
        for key in self.stock_data.keys():
            print('{}  {}  {}  {}'.format(key, self.stock_data[key][0], self.stock_data[key][1],self.stock_data[key][2]))

    def gamer_papers(self, g):
        print('Posiadasz papiery: ')
        temp = 0
        for key in g.papers_possessed.keys():

            if g.papers_possessed[key] != 0:
                print(key,": ", g.papers_possessed[key])
                temp = 1
        if temp == 0:
            print('Niestety jeszcze zadnych nie posiadasz!')

    def gamer_sell(self, g, sym, number, price):
        if g.papers_possessed[sym] < number:
            print("Nie posiadasz wystarczajacej liczby papierow!")
        else:
            g.add_papers_toSell(sym, number, price)
            print('Dodano papiery do oferty sprzedazy!')

    def gamer_buy(self,g, sym, number, price):
        if g.money_res + price * number > g.money:
            print('Nie posiadasz wystarczajacej ilosci zlotych monet!')
        else:
            g.add_papers_toBuy(sym, number, price)
            print("Dodano papiery do oferty kupna!")


g = Game()
g.play_game()

