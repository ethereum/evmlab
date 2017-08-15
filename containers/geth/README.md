### GethVM

This is the Geth EVM docker image. 

To execute the geth `evm`: 

	$docker run gethvm --code "6040" --json run

To execute with a specifiec `codefile`, you need to also make the file accessible to the docker container. 

Here's some code we want to execute (on the host)

	$echo "6040"  > /tmp/tempcode

Here's how to mount and run it 

	$docker run -v /tmp/tempcode:/code gethvm --json --codefile /code run


	{"pc":0,"op":96,"gas":"0x2540be400","gasCost":"0x3","memory":"0x","memSize":0,"stack":[],"depth":1,"error":null,"opName":"PUSH1"}
	{"pc":2,"op":0,"gas":"0x2540be3fd","gasCost":"0x0","memory":"0x","memSize":0,"stack":["0x40"],"depth":1,"error":null,"opName":"STOP"}
	{"output":"","gasUsed":"0x3","time":142595}

