# EVM lab utilities

This package contains various tools to interact with the Ethereum virtual machine. 

# Compiler

The 'compiler' is a tool to build evm binaries, using a pythonic way to construct the programs using assembly. 

Here's an example that tests `ecdsaRecover`:

```python

	p = compiler.Program()
	p.mstore(0 ,0x38d18acb67d25c8bb9942764b62f18e17054f66a817bd4295423adf9ed98873e)
	v = 0x000000000000000000000000000000000000000000000000000000000000001b
	p.mstore(32   , v)
	p.mstore(64   ,0x723841761d213b60ac1cbf063207cbeba6c2725bcaf7c189e63f13d93fc1dc07)
	p.mstore(96   ,0x789d1dd423d25f0772d2748d60f7e4b81bb14d086eba8e8e8efb6dcff8a4ae02)
	p.call(0xfff,1,0,0,0x80,0x80,0x20)
	p.rreturn(140,20)
	code = p.bytecode()
```

Here's an example of stuffing `JUMPDEST` into a program: 

```python

	p = compiler.Program()
	p.jump(0x3)
	p.jumpdest()
	p.rreturn()
	for i in range(0,20000):
		p.op(JUMPDEST)

	return p.bytecode()

```

# Gethvm

The `gethvm` provides some ability to execute the `evm` from geth. 
Example: 

```python

     vm = gethvm.VM(evmbin)
     output =  vm.execute(code = bootstrap, genesis = g_path, json = True)
``` 

# Etherchain

The `etherchain` package contains an API for interacting with the Etherchain API. 

# Reproduce

An example app is `reproduce.py` which can reproduce an on-chain transaction as a totally local event, and run it in the `evm`. 

The app takes a `txhash`, and 

1 Fetch the transaction data from an API. 
2 Mark (source, destination) as need-to-fetch
3 Fetch balance and nonce at source, add to `genesis`
4 Execute transaction on the `evm`
5 If transaction has any externally reaching ops (BALANCE, EXTCODECOPY, CALL etc), 
  * Add those accounts as need-to-fetch
6. Go back to 3 until the execution does not result in any more accounts to be fetched. 
7. Save the transaction trace and genesis

