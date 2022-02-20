
```bash
# Testing command in docker:
# pip install -e .
# ~/.local/bin/bt install
# chromium-browser --load-extension=/brotab/brotab/extension/chrome --headless --use-gl=swiftshader --disable-software-rasterizer --disable-dev-shm-usage --no-sandbox --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 https://www.chromestatus.com/
# xvfb-chromium --no-sandbox --load-extension=/brotab/brotab/extension/chrome --use-gl=swiftshader --disable-software-rasterizer --disable-dev-shm-usage --no-sandbox --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 https://www.chromestatus.com/

# chromium --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=19222 https://ipinfo.io/json
# chromium --no-sandbox --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=19222 https://ipinfo.io/json
# docker run -v "$(pwd):/brotab" -p 19222:9222 -it --rm --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm --security-opt seccomp=$(pwd)/chrome.json brotab-integration chromium --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 https://ipinfo.io/json
# docker run -v "$(pwd):/brotab" -p 19222:9222 -it --rm --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm brotab-integration chromium --no-sandbox --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 https://ipinfo.io/json

# jess
# docker run -it --rm --net host --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm --security-opt seccomp=$(pwd)/chrome.json --name chromium brotab-integration
# working option:
# docker run -it --rm --net host --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm --security-opt seccomp=$(pwd)/chrome.json brotab-integration --remote-debugging-address=0.0.0.0 --remote-debugging-port=19222 --disable-gpu https://ipinfo.io/json

# Run docker:
# docker run -v "$(pwd):/brotab" -p 19222:9222 -p 14625:4625 -it --rm --cpuset-cpus 0 --memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY -v /dev/shm:/dev/shm brotab-integration

# Inside:
# pip install -e .
# bt install --tests
# chromium --no-sandbox --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=19222 --load-extension=/brotab/brotab/extension/chrome file:///

# chromium --no-sandbox --disable-gpu --remote-debugging-address=0.0.0.0 --remote-debugging-port=19222 --load-extension=/brotab/brotab/extension/chrome https://ipinfo.io/json

# socat TCP4-LISTEN:8000,fork,reuseaddr,bind=172.17.0.2 TCP4:127.0.0.1:8000

# python3 -m http.server --bind ::
# python3 -m http.server --bind 172.17.0.2

#	-v $HOME/Downloads:/home/chromium/Downloads \
#	-v $HOME/.config/chromium/:/data \ # if you want to save state
#	--security-opt seccomp=$HOME/chrome.json \
#	--device /dev/snd \ # so we have sound

# Remote:
# http://0.0.0.0:19222/devtools/inspector.html?ws=localhost:19222/devtools/page/AEDF6B9CB4D1DD63E26826BBA3EC50B5


```
