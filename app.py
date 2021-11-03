import hashlib

# Related to coin signing
from blspy import G2Element

from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.rpc.full_node_rpc_client import FullNodeRpcClient

from chia.util.config import load_config
from chia.util.bech32m import decode_puzzle_hash
from chia.util.default_root import DEFAULT_ROOT_PATH

from chia.types.coin_spend import CoinSpend
from chia.types.spend_bundle import SpendBundle

from password.password_driver import (
    create_coin_puzzle,
    create_coin_treehash,
    create_coin_txaddress,
    solution_for_password,
    create_coin_password_hash_from_string
)
import asyncio

from quart import Quart, render_template, request, url_for, redirect

# Instantiate the app
app = Quart(__name__)

# ========================================================
# GLOBAL VARIABLES
# ========================================================
full_node_rpc_client = None
wallet_rpc_client = None

config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
wallet_host = "localhost"
wallet_rpc_port = config["wallet"]["rpc_port"]
node_rpc_port = config["full_node"]["rpc_port"]

# ========================================================
# HELPER METHODS
# ========================================================


async def setup_blockchain_connection():
    global full_node_rpc_client, wallet_rpc_client

    # Should not create new connection if already connected
    if full_node_rpc_client is not None and wallet_rpc_client is not None:
        return

    # Setup the RPC connections
    full_node_rpc_client = await FullNodeRpcClient.create(wallet_host, node_rpc_port, DEFAULT_ROOT_PATH, config)
    wallet_rpc_client = await WalletRpcClient.create(wallet_host, wallet_rpc_port, DEFAULT_ROOT_PATH, config)

# ========================================================
# QUART APPLICATION
# ========================================================


@app.route('/')
async def index():
    await setup_blockchain_connection()

    wallets = await wallet_rpc_client.get_wallets()
    balance = await wallet_rpc_client.get_wallet_balance(wallets[0]["id"])

    return await render_template('index.html', balances=[balance['confirmed_wallet_balance'] / 1000000000000])


@app.route('/create', methods=('GET', 'POST'))
async def create():
    await setup_blockchain_connection()

    # If a post request was made
    if request.method == 'POST':
        # Get variables from the form
        password = (await request.form)['password']
        amount = (await request.form)['amount']

        # Get information for coin transaction
        coin_txaddress = create_coin_txaddress(
            create_coin_password_hash_from_string(password))

        # Get the ID of the wallet we will transact with
        wallets = await wallet_rpc_client.get_wallets()
        wallet_id = str(wallets[0]["id"])

        # Try to send the transaction to the network
        tx = await wallet_rpc_client.send_transaction(wallet_id, int(amount), coin_txaddress)

        # Redirect back to the home page on success
        return redirect(url_for('index'))

    # Show the create from template
    # For GET method
    return await render_template('create.html')


@app.route('/spend', methods=('GET', 'POST'))
async def spend():
    await setup_blockchain_connection()

    # If a post request was made
    if request.method == 'POST':
        # Get variables from the form
        password = (await request.form)['password']
        address = (await request.form)['address']

        # Get Spend Bundle Parameters
        coin_reveal = create_coin_puzzle(
            create_coin_password_hash_from_string(password))
        coin_treehash = create_coin_treehash(
            create_coin_password_hash_from_string(password))
        coin_records = await full_node_rpc_client.get_coin_records_by_puzzle_hash(coin_treehash)

        # Let's spend the first available coin with this password
        # Note: Since all coins with the same password created with the puzzle in /password/password.clsp have the same
        #       puzzle_hash they will all be retrieved here. Even the ones that were NOT created by you!
        coin_to_spend = None
        for coin_record in coin_records:
            if not coin_record.spent:
                coin_to_spend = coin_record
                break

        # If there's no coin redirect back to the spend template
        if coin_to_spend == None:
            print("NO COIN AVAILABLE")
            # TODO: Show error on client
            return await render_template('spend.html')

        # Get the coin solution
        decoded_address = decode_puzzle_hash(address)
        coin_solution = solution_for_password(
            coin_to_spend.coin, password, decoded_address)

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
        await full_node_rpc_client.push_tx(tx_spend_bundle)

        # Redirect back to the home page on success
        return redirect(url_for('index'))

    # Show the spend form template
    # If GET method
    return await render_template('spend.html')

# This will run the app when this file is runned
app.run()
