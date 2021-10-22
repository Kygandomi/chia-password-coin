import pytest

from typing import Dict, List, Optional
from chia.types.blockchain_format.coin import Coin
from chia.types.spend_bundle import SpendBundle

from cdv.test import CoinWrapper
from cdv.test import setup as setup_test

from password.password_driver import (
    create_password_puzzle,
    solution_for_password,
)

import hashlib

class TestSomething:
    @pytest.fixture(scope="function")
    async def setup(self):
        network, alice, bob = await setup_test()
        await network.farm_block()
        yield network, alice, bob

    @pytest.mark.asyncio
    async def test_create_and_spend_password_coin(self, setup):
        network, alice, bob = setup
        try:
            # Get our alice wallet some money
            await network.farm_block(farmer=alice)

            # Create Password Coin 
            # This will use 500 mojos to create our password on the test blockchain.
            password_coin: Optional[CoinWrapper] = await alice.launch_smart_coin(
                create_password_puzzle(bytes.fromhex(hashlib.sha256("chiaiscool".encode()).hexdigest())),
                amt=500
            ) 
            
            # Make sure everything succeeded
            if not password_coin:
                raise ValueError("Something went wrong launching/choosing a coin")

            # This is the spend of the piggy bank coin.  We use the driver code to create the solution.
            password_spend: SpendBundle = await alice.spend_coin(
                password_coin,
                pushtx=False, # Don't immediately push the coin to the network
                args=solution_for_password(password_coin.as_coin(), "chiaiscool", alice.puzzle_hash),
            )

            # Spend Passowrd Coin
            result = await network.push_tx(password_spend)
            
            # Make some assertions
            assert "error" not in result

            # # Make sure there is exactly one coin that has been cashed out to alice
            filtered_result: List[Coin] = list(
                filter(
                    lambda addition: (addition.amount == 500) and (addition.puzzle_hash == alice.puzzle_hash),
                    result["additions"],
                )
            )
            assert len(filtered_result) == 1

        finally:
            await network.close()

