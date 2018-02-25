
TARGET=~/.mozilla/native-messaging-hosts/firefox_mediator.json

install:
	install firefox_mediator.json $(TARGET)
	sed -i 's|$$HOME|$(HOME)|' $(TARGET)
