from chia.types.blockchain_format.coin import Coin
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.types.blockchain_format.program import Program

from chia.util.bech32m import encode_puzzle_hash

from cdv.util.load_clvm import load_clvm

PASSWORD_MOD = load_clvm("password.clsp", "password")

# Create a password coin -- returns curried version of the puzzle
def create_password_puzzle(PASSWORD_HASH):
  return PASSWORD_MOD.curry(PASSWORD_HASH)


# Create a password coin -- returns curried version of the puzzle
def create_password_treehash(PASSWORD_HASH):
  return PASSWORD_MOD.curry(PASSWORD_HASH).get_tree_hash()

# Create a password coin -- returns curried version of the puzzle
def create_password_txaddress(PASSWORD_HASH):
  treehash = PASSWORD_MOD.curry(PASSWORD_HASH).get_tree_hash()
  return encode_puzzle_hash(treehash, 'txch')

# Generate a solution to spend password coin
def solution_for_password(password_coin, password, receive_puzhash):
  return Program.to([password, receive_puzhash, password_coin.amount])