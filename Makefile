

all:
	echo ALL

reset:
	pkill python3; pkill xvfb-run; pkill node; pkill Xvfb; pkill firefox

switch_to_dev:
	echo "Switching to DEV"

switch_to_prod:
	echo "Switching to PROD"

.PHONY: reset switch_to_dev switch_to_prod
