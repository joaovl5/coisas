from coisas.main import run

run("ping -c 4 -w 4 1.1.1.1")
run("ls ~")

home = "_home"
glob = {"type": "glob", "value": "./**"}

run(t"ls {home} {glob}")
