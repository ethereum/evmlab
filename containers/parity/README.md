### ParityVM

This is the Parity EVM docker image. 

To execute the parity `evm`: 

	$docker run holiman/parityvm --code "6040" --json run

	{"pc":0,"op":96,"opName":"PUSH1","gas":"0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","gasCost":"0x3","memory":"0x","stack":[],"storage":{},"depth":1}
	{"pc":0,"op":96,"opName":"PUSH1","gas":"0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffc","gasCost":"0x0","memory":"0x","stack":["0x40"],"storage":{},"depth":1}
	{"output":"0x","gasUsed":"0x3","time":116}


To see options: 

	$docker run holiman/parityvm stats -h
	EVM implementation for Parity.
	  Copyright 2016, 2017 Parity Technologies (UK) Ltd

	Usage:
	    evmbin stats [options]
	    evmbin [options]
	    evmbin [-h | --help]

	Transaction options:
	    --code CODE        Contract code as hex (without 0x).
	    --to ADDRESS       Recipient address (without 0x).
	    --from ADDRESS     Sender address (without 0x).
	    --input DATA       Input data as hex (without 0x).
	    --gas GAS          Supplied gas as hex (without 0x).
	    --gas-price WEI    Supplied gas price as hex (without 0x).

	General options:
	    --json             Display verbose results in JSON.
	    --chain CHAIN      Chain spec file path.
	    -h, --help         Display this message and exit.
