import os
import logging
import platform


logger = logging.getLogger('brotab')


def make_windows_path(path):
    return path.replace('/', os.sep)


def make_windows_path_double_sep(path):
    return path.replace('/', os.sep * 2).replace('\\', os.sep * 2)


def windows_registry_set_key(key_path, value):
    from winreg import CreateKey, SetValue, HKEY_CURRENT_USER, REG_SZ
    with CreateKey(HKEY_CURRENT_USER, key_path) as sub_key:
        SetValue(sub_key, None, REG_SZ, value)


def register_native_manifest_windows_chrome(manifest_filename):
    key_path = r'Software\Google\Chrome\NativeMessagingHosts\brotab_mediator'
    manifest_filename = make_windows_path(manifest_filename)
    logger.info('Setting registry key "%s" to "%s"', key_path, manifest_filename)
    print('Setting registry key "%s" to "%s"' % (key_path, manifest_filename))
    windows_registry_set_key(key_path, manifest_filename)

def register_native_manifest_windows_brave(manifest_filename):
    key_path = r'Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\brotab_mediator'
    manifest_filename = make_windows_path(manifest_filename)
    logger.info('Setting registry key "%s" to "%s"', key_path, manifest_filename)
    print('Setting registry key "%s" to "%s"' % (key_path, manifest_filename))
    windows_registry_set_key(key_path, manifest_filename)


def register_native_manifest_windows_firefox(manifest_filename):
    key_path = r'Software\Mozilla\NativeMessagingHosts\brotab_mediator'
    manifest_filename = make_windows_path(manifest_filename)
    logger.info('Setting registry key "%s" to "%s"', key_path, manifest_filename)
    print('Setting registry key "%s" to "%s"' % (key_path, manifest_filename))
    windows_registry_set_key(key_path, manifest_filename)


def is_windows() -> bool:
    return platform.system() == 'Windows'


def get_editor() -> str:
    mapping = {
        'Windows': 'notepad'
    }
    system = platform.system()
    editor = mapping.get(system, 'nvim')
    return os.environ.get('EDITOR', editor)
