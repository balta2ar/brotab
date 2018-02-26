
TARGET_FIREFOX=~/.mozilla/native-messaging-hosts/brotab_mediator.json
TARGET_CHROMIUM=~/.config/chromium/NativeMessagingHosts/brotab_mediator.json
TARGET_CHROME=~/.config/google-chrome/NativeMessagingHosts/brotab_mediator.json

install_firefox:
	mkdir -p $(dir $(TARGET_FIREFOX))
	install firefox_mediator.json $(TARGET_FIREFOX)
	sed -i 's|$$PWD|$(PWD)|' $(TARGET_FIREFOX)

install_chromium:
	mkdir -p $(dir $(TARGET_CHROMIUM))
	install chromium_mediator.json $(TARGET_CHROMIUM)
	sed -i 's|$$PWD|$(PWD)|' $(TARGET_CHROMIUM)

install_chrome:
	mkdir -p $(dir $(TARGET_CHROME))
	install chromium_mediator.json $(TARGET_CHROME)
	sed -i 's|$$PWD|$(PWD)|' $(TARGET_CHROME)

install: install_firefox install_chromium install_chrome
