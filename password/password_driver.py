import hashlib

from chia.types.blockchain_format.program import Program
from chia.util.bech32m import encode_puzzle_hash
from cdv.util.load_clvm import load_clvm

# Load the Chialisp puzzle code
PASSWORD_MOD = load_clvm("password.clsp", "password")


def create_coin_puzzle(PASSWORD_HASH):
    """ Return curried version of the puzzle
    """

    return PASSWORD_MOD.curry(PASSWORD_HASH)


def create_coin_treehash(PASSWORD_HASH):
    """ Return treehash for the puzzle
    """

    return create_coin_puzzle(PASSWORD_HASH).get_tree_hash()


def create_coin_txaddress(PASSWORD_HASH, address_prefix='txch'):
    """ Return puzzle address
    """

    return encode_puzzle_hash(create_coin_treehash(PASSWORD_HASH), address_prefix)


def create_coin_password_hash_from_string(password):
    """ Return password hash
    """

    return bytes.fromhex(hashlib.sha256(password.encode()).hexdigest())


def solution_for_password(password_coin, password, receive_puzhash):
    """ Return puzzle solution
    """

    return Program.to([password, receive_puzhash, password_coin.amount])
