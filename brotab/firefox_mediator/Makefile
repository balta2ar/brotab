
TARGET_FIREFOX=~/.mozilla/native-messaging-hosts/firefox_mediator.json
TARGET_CHROMIUM=~/.config/chromium/NativeMessagingHosts/firefox_mediator.json

install_firefox:
	mkdir -p $(dir $(TARGET_FIREFOX))
	install firefox_mediator.json $(TARGET_FIREFOX)
	sed -i 's|$$PWD|$(PWD)|' $(TARGET_FIREFOX)

install_chromium:
	mkdir -p $(dir $(TARGET_CHROMIUM))
	install firefox_mediator.json $(TARGET_CHROMIUM)
	sed -i 's|$$PWD|$(PWD)|' $(TARGET_CHROMIUM)

install: install_firefox install_chromium
