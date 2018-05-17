#/bin/bash

cd /app/


cat << EOF

This is a docker image specifically to run opviewer and/or the reproducer tool. It will drop you into a bash shell. 
It comes bundled with an evm, located at /evm. This can be used to run traces. 


Examples of what you can do is:

./opviewer.py --hash 0x9dbf0326a03a2a3719c27be4fa69aacc9857fd231a8d9dcaede4bb083def75ec -g /evm --no-docker

That command will, under the hood, invoke the reproducer and then the show the opviewer for the final trace. 
If you want to _only_ run the reproducer, try: 

./reproducer.py --hash 0x9dbf0326a03a2a3719c27be4fa69aacc9857fd231a8d9dcaede4bb083def75ec -g /evm --no-docker

Please file issues or PR to improve evmlab to https://github.com/holiman/evmlab 

EOF

/bin/bash
