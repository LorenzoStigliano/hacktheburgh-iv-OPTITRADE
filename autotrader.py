import socket
import select
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression

REMOTE_IP = "35.179.45.135"
UDP_ANY_IP = ""

USERNAME = "Team34"
PASSWORD = "AJDdrCpk"


# -------------------------------------
# EML code (EML is execution market link)
# -------------------------------------

EML_UDP_PORT_LOCAL = 8078
EML_UDP_PORT_REMOTE = 8001

eml_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
eml_sock.bind((UDP_ANY_IP, EML_UDP_PORT_LOCAL))


# -------------------------------------
# IML code (IML is information market link)
# -------------------------------------

IML_UDP_PORT_LOCAL = 7078
IML_UDP_PORT_REMOTE = 7001
IML_INIT_MESSAGE = "TYPE=SUBSCRIPTION_REQUEST"

iml_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
iml_sock.bind((UDP_ANY_IP, IML_UDP_PORT_LOCAL))


# -------------------------------------
# Auto trader
# -------------------------------------
# Sell
price_sell_sp_future, volume_sell_sp_future = [], []
# Buy
price_buy_sp_future, volume_buy_sp_future = [], []
# Sell
price_sell_esx, volume_sell_esx = [], []
# Buy
price_buy_esx, volume_buy_esx = [], []

#Trade
trade_price_sp_future, trade_volume_sp_future, trade_side_sp_futures = [], [], []

trade_price_esx, trade_volume_esx, trade_side_esx = [], [], []

sp_market_direction, esx_market_direction = 0, 0

position_sp, position_esx = 0, 0


def general_direction_market(price_sell_future):
    X = np.array(range(len(price_sell_future))).reshape(-1, 1)
    y = price_sell_future
    model = LinearRegression().fit(X, y)
    return model.coef_


def start_autotrader():
    iteration = 0
    subscribe()
    while True:
        if iteration !=0:
            sp_market_direction = general_direction_market(price_sell_sp_future)
            esx_market_direction = general_direction_market(price_sell_esx)
            period_of_observation(sp_market_direction,esx_market_direction,iteration)
            iteration += 1
        else:
            period_of_observation(0,0,iteration)
            iteration +=1

        print("Current Position with SP_FUTURE: " + str(position_sp))
        print("Current Position with ESX_FUTURE: " + str(position_esx))


def subscribe():
    iml_sock.sendto(IML_INIT_MESSAGE.encode(), (REMOTE_IP, IML_UDP_PORT_REMOTE))


def period_of_observation(sp_market_dir,esx_market_dir,iteration):
    """
    Wait for messages from the exchange and
    call handle_message on each of them.
    """

    if iteration !=0:
        for i in range(30):
            ready_socks, _, _ = select.select([iml_sock, eml_sock], [], [])

            for socket in ready_socks:
                data, addr = socket.recvfrom(1024)
                message = data.decode('utf-8')
                data_communication = read_data(message)
                add_data(data_communication)

                if data_communication["type"] == "TYPE=PRICE":
                    if data_communication["product"] == "SP-FUTURE":
                        sp_sell = data_communication["bid_price"]
                        sp_buy = data_communication["ask_price"]
                        decision(sp_market_dir, price_buy_sp_future, price_sell_sp_future, sp_buy, sp_sell,
                                 "SP-FUTURE")
                    else:
                        esx_sell = data_communication["bid_price"]
                        esx_buy = data_communication["ask_price"]
                        decision(esx_market_dir, price_buy_esx, price_sell_esx, esx_buy, esx_sell,
                                 "ESX-FUTURE")

    else:
        for i in range(10):
            ready_socks, _, _ = select.select([iml_sock, eml_sock], [], [])
            for socket in ready_socks:
                data, addr = socket.recvfrom(1024)
                message = data.decode('utf-8')
                data_communication = read_data(message)
                add_data(data_communication)


def decision(direction, price_buy_future, price_sell_future, current_buy, current_sell,future):

    global position_sp
    global position_esx

    lifetime_mean_buy_price = np.mean(price_buy_future)
    lifetime_mean_sell_price = np.mean(price_sell_future)
    lifetime_sd_buy_price = np.std(price_buy_future)
    lifetime_sd_sell_price = np.std(price_sell_future)

    if future == "SP-FUTURE":
        # Sell
        if direction > 0:
            if current_sell > 1.5 * lifetime_sd_sell_price + lifetime_mean_sell_price and (position_sp > 0 and position_sp < 4):
                send_order(future, "SELL", current_sell, 50)
                position_sp -= 1
                print("SELLING")
        # Buy
        if direction < 0:
            if current_buy < 1.5 * lifetime_sd_buy_price + lifetime_mean_buy_price and (position_sp == 0 or position_sp == 1 or position_sp == 2):
                send_order(future, "BUY", current_buy, 50)
                position_sp += 1
                print("BUYING")
    else:
        # Sell
        if direction > 0:
            if current_sell > 1.5 * lifetime_sd_sell_price + lifetime_mean_sell_price and (position_esx > 0 and position_esx < 4):
                send_order(future, "SELL", current_sell, 50)
                position_esx -= 1
                print("SELLING")
        # Buy
        if direction < 0:
            if current_buy < 1.5 * lifetime_sd_buy_price + lifetime_mean_buy_price and (position_esx == 0 or position_esx == 1 or position_esx == 2):
                send_order(future, "BUY", current_buy, 50)
                position_esx += 1
                print("BUYING")


def add_data(data_formatted):
    if data_formatted["type"] == "TYPE=PRICE" :
        if data_formatted["product"] == "SP-FUTURE":
            price_sell_sp_future.append(data_formatted["bid_price"])
            volume_sell_sp_future.append(data_formatted["bid_volume"])
            price_buy_sp_future.append(data_formatted["ask_price"])
            volume_buy_sp_future.append(data_formatted["ask_volume"])
        else:
            price_sell_esx.append(data_formatted["bid_price"])
            volume_sell_esx.append(data_formatted["bid_volume"])
            price_buy_esx.append(data_formatted["ask_price"])
            volume_buy_esx.append(data_formatted["ask_volume"])

    else:
        if data_formatted["product"] == "SP-FUTURE":
            trade_price_sp_future.append(data_formatted["price"])
            trade_volume_sp_future.append(data_formatted["volume"])
            trade_side_sp_futures.append(data_formatted["side"])
        if data_formatted["product"] == "ESX-FUTURE":
            trade_price_esx.append(data_formatted["price"])
            trade_volume_esx.append(data_formatted["volume"])
            trade_side_esx.append(data_formatted["side"])


def read_data(message):
    comps = message.split("|")

    type = comps[0]

    if type == "TYPE=ORDER_ACK":

        return {"type": "TYPE=ORDER_ACK","product":"NA"}

    if type == "TYPE=PRICE":
        feedcode = comps[1].split("=")[1]
        bid_price = float(comps[2].split("=")[1])
        bid_volume = int(comps[3].split("=")[1])
        ask_price = float(comps[4].split("=")[1])
        ask_volume = int(comps[5].split("=")[1])

        dict = {"type": type, "product": feedcode, "bid_volume": bid_volume, "bid_price": bid_price,
                "ask_volume": ask_volume, "ask_price": ask_price}

        return dict

    if type == "TYPE=TRADE":
        feedcode = comps[1].split("=")[1]
        side = comps[2].split("=")[1]
        traded_price = float(comps[3].split("=")[1])
        traded_volume = int(comps[4].split("=")[1])

        dict = {"type": type, "product": feedcode, "side": side, "price": traded_price, "volume": traded_volume}

        return dict


def handle_message(message):
    comps = message.split("|")

    if len(comps) == 0:
        print(f"Invalid message received: {message}")
        return

    type = comps[0]

    if type == "TYPE=PRICE":

        feedcode = comps[1].split("=")[1]
        bid_price = float(comps[2].split("=")[1])
        bid_volume = int(comps[3].split("=")[1])
        ask_price = float(comps[4].split("=")[1])
        ask_volume = int(comps[5].split("=")[1])

        print(f"[PRICE] product: {feedcode} bid: {bid_volume}@{bid_price} ask: {ask_volume}@{ask_price}")

    if type == "TYPE=TRADE":

        feedcode = comps[1].split("=")[1]
        side = comps[2].split("=")[1]
        traded_price = float(comps[3].split("=")[1])
        traded_volume = int(comps[4].split("=")[1])

        print(f"[TRADE] product: {feedcode} side: {side} price: {traded_price} volume: {traded_volume}")

    if type == "TYPE=ORDER_ACK":

        if comps[1].split("=")[0] == "ERROR":
            error_message = comps[1].split("=")[1]
            print(f"Order was rejected because of error {error_message}.")
            return

        feedcode = comps[1].split("=")[1]
        traded_price = float(comps[2].split("=")[1])

        # This is only 0 if price is not there, and volume became 0 instead.
        # Possible cause: someone else got the trade instead of you.
        if traded_price == 0:
            print(f"Unable to get trade on: {feedcode}")
            return

        traded_volume = int(comps[3].split("=")[1])

        print(f"[ORDER_ACK] feedcode: {feedcode}, price: {traded_price}, volume: {traded_volume}")


def send_order(target_feedcode, action, target_price, volume):
    """
    Send an order to the exchange.
    :param target_feedcode: The feedcode, either "SP-FUTURE" or "ESX-FUTURE"
    :param action: "BUY" or "SELL"
    :param target_price: Price you want to trade at
    :param volume: Volume you want to trade at. Please start with 10 and go from there. Don't go crazy!
    :return:
    Example:
    If you want to buy  100 SP-FUTURES at a price of 3000:
    - send_order("SP-FUTURE", "BUY", 3000, 100)
    """
    order_message = f"TYPE=ORDER|USERNAME={USERNAME}|PASSWORD={PASSWORD}|FEEDCODE={target_feedcode}|ACTION={action}|PRICE={target_price}|VOLUME={volume}"
    print(f"[SENDING ORDER] {order_message}")
    eml_sock.sendto(order_message.encode(), (REMOTE_IP, EML_UDP_PORT_REMOTE))


# -------------------------------------
# Main
# -------------------------------------

if __name__ == "__main__":
    start_autotrader()
