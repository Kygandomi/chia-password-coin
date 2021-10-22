import hashlib

from blspy import G2Element

from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient

from chia.util.config import load_config
from chia.util.bech32m import decode_puzzle_hash
from chia.util.default_root import DEFAULT_ROOT_PATH

from chia.types.coin_spend import CoinSpend
from chia.types.spend_bundle import SpendBundle

from password.password_driver import (
    create_password_puzzle,
    create_password_treehash,
    create_password_txaddress,
    solution_for_password,
)

from quart import Quart, render_template, request, url_for, redirect

app = Quart(__name__)

# ========================================================
# GLOBAL VARIABLES
# ========================================================
main_wallet = {}
config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
wallet_host = "localhost"
wallet_rpc_port = config["wallet"]["rpc_port"]
node_rpc_port = config["full_node"]["rpc_port"]

# ========================================================
# HELPER METHODS
# ========================================================

async def get_rpc_node():
   return await FullNodeRpcClient.create( wallet_host, node_rpc_port, DEFAULT_ROOT_PATH, config )

# Helper method for getting Wallet RPC client
async def get_rpc_client():
    return await WalletRpcClient.create( wallet_host, wallet_rpc_port, DEFAULT_ROOT_PATH, config )

# Helper method for requesting vallue
async def get_wallet():

    # Get the RPC Client
    client = await get_rpc_client()

    # We're just going to use the first wallet which seems to always be the one currently open in the chia gui
    wallets = await client.get_wallets()
    
    balance = await client.get_wallet_balance(wallets[0]["id"])

    my_wallet = {}
    my_wallet['client'] = client
    my_wallet['wallet'] =  wallets[0]
    my_wallet['id'] = wallets[0]['id']
    my_wallet['name'] = wallets[0]['name']
    my_wallet['balance'] = balance['confirmed_wallet_balance']

    # Close the client    
    client.close()

    return my_wallet

# ========================================================
# QUART APPLICATION
# ========================================================

@app.route('/')
async def index():
    global main_wallet

    # If we don't already have the wallet info
    if len(main_wallet.keys()) == 0:
      main_wallet = await get_wallet()

    # return await render_template('index.html', wallets=[main_wallet['wallet']])
    return await render_template('index.html', wallets=[main_wallet['balance'] / 1000000000000])

@app.route('/create', methods=('GET', 'POST'))
async def create():
    # If a post request was made
    if request.method == 'POST':
          # Get variables from the form
          password = (await request.form)['password']
          amount = (await request.form)['amount']

          # Get information for coin transaction
          coin_txaddress = create_password_txaddress(bytes.fromhex(hashlib.sha256(password.encode()).hexdigest()))
          
          # Get the RPC Client
          client = await get_rpc_client()

          # Try to send the transaction to the network
          tx = await client.send_transaction(str(main_wallet['id']), int(amount), coin_txaddress)
          
          print("TX COMPLETED - COIN CREATED !")
          print(tx.name)

          # Close client
          client.close() 

          # Redirect back to the home page on success
          return redirect(url_for('index'))

    # Show the create form template
    return await render_template('create.html')


@app.route('/spend', methods=('GET', 'POST'))
async def spend():
    # If a post request was made
    if request.method == 'POST':
          # Get variables from the form
          password = (await request.form)['password']
          address = (await request.form)['address']

          # Get the RPC Clients
          client = await get_rpc_client()
          node = await get_rpc_node()

          # Get Spend Bundle Parameters
          coin_reveal = create_password_puzzle(bytes.fromhex(hashlib.sha256(password.encode()).hexdigest()))

          coin_treehash = create_password_treehash(bytes.fromhex(hashlib.sha256(password.encode()).hexdigest()))
          coin_records = await node.get_coin_records_by_puzzle_hash(coin_treehash)

          # Let's spend the first available coin with this password
          coin_to_spend = None
          for coin_record in coin_records:
            if not coin_record.spent:
              coin_to_spend = coin_record

          # If there's no coin redirect back to the spend template
          if coin_to_spend == None:
            print("NO COIN AVAILABLE")
            node.close()
            client.close()
            return await render_template('spend.html')

          # Get the coin solution
          decoded_address = decode_puzzle_hash(address)
          coin_solution = solution_for_password(coin_to_spend.coin, password, decoded_address)

          # Put together our spend bundle
          tx_spend_bundle = SpendBundle(
              [
                  CoinSpend(
                      coin_to_spend.coin,
                      coin_reveal,
                      coin_solution,
                  )
              ],
              G2Element(),
          )

          # Try to send the spend bundle to the network
          push_res = await node.push_tx(tx_spend_bundle)

          print("TX COMPLETED - SPEND BUNDLE SUBMITTED")
          print(tx_spend_bundle)
          print(push_res)

          # Close clients
          node.close()
          client.close() 

          # Redirect back to the home page on success
          return redirect(url_for('index'))

    # Show the spend form template
    return await render_template('spend.html')