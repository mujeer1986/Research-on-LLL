#!/usr/bin/python3

import web3
from tqdm import tqdm

import rlp
import ethereum
import ethereum.transactions
import os

w3 = web3.Web3(web3.IPCProvider("/large/joachim/ethereum-datadir/geth.ipc", timeout=60))

# first block with transactions
first_block = 46147

# first block not done last round
first_block = 6724062+1

#last_block = w3.eth.blockNumber
last_block = w3.eth.syncing["currentBlock"]
# highest_block = w3.eth.syncing["highestBlock"]
# 
# print("Have blocks until %d, (total %d)" % (last_block, highest_block))


# Based on https://ethereum.stackexchange.com/a/22892
class MyTransaction(ethereum.transactions.Transaction):
    _signhash = None
    def sighash(self):
        secpk1n = ethereum.transactions.secpk1n
        if not self._signhash:
            if self.v in (27, 28):
                vee = self.v
                rlpdata = rlp.encode(
                    self, ethereum.transactions.UnsignedTransaction)
            elif self.v >= 37:
                vee = self.v - self.network_id * 2 - 8
                assert vee in (27, 28)
                rlpdata = rlp.encode(
                    rlp.infer_sedes(self).serialize(self)[:-3] \
                    + [self.network_id, '', ''])
            else:
                return None  # Invalid V value
            if self.r >= secpk1n or self.s >= secpk1n or self.r == 0 \
                    or self.s == 0:
                return None  # Invalid signature values!
            self._sighash = ethereum.utils.sha3(rlpdata)
        return self._sighash

    _publickey = None
    def publickey(self):
        if not self._publickey:
            if self.v in (27, 28):
                vee = self.v
            elif self.v >= 37:
                vee = self.v - self.network_id * 2 - 8
                assert vee in (27, 28)
            else:
                return None  # Invalid V value
            pub = ethereum.utils.ecrecover_to_pub(self.sighash(), vee, self.r, self.s)
            if pub == b'\x00' * 64:
                return None  # Invalid signature (zero privkey cannot sign)
            self._publickey = pub
        return self._publickey

filename = 'hashes-from-txid-hash-v-r-s-blocks-%d-to-%d.txt' % (first_block,last_block)
hashes = open(filename + '.tmp','w')

#for block in range(first_block,last_block+1):
for block in tqdm(range(first_block,last_block+1)):
    n = w3.eth.getBlockTransactionCount(block)
    for txn in range(0,n):
        tx = w3.eth.getTransactionByBlock(block,txn)
        #print(tx)
        to = tx['to'] if tx['to'] else b''
        txo = MyTransaction(tx['nonce'], tx['gasPrice'], tx['gas'],
                            to, tx['value'], bytes.fromhex(tx.input[2:]),
                            tx['v'], int(tx['r'].hex(),16), int(tx['s'].hex(),16))
        #assert txo.hash == tx.hash
        #from_address = ethereum.utils.sha3(txo.publickey())[-20:].hex()
        # print (from_address, tx['from'][2:].lower())
        #assert from_address == tx['from'][2:].lower()
        hashes.write("%s %s %s %d %s %s\n" % (tx['from'], tx['hash'].hex(), txo.sighash().hex(), tx['v'], tx['r'].hex(), tx['s'].hex()))
        #hashes.write("%s %s %s %s %d %s %s\n" % (tx['from'], txo.publickey().hex(), tx['hash'].hex(), txo.sighash().hex(), tx['v'], tx['r'].hex(), tx['s'].hex()))


hashes.close()
os.rename(filename + '.tmp', filename)
