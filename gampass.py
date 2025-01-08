import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from unopass import unopass as secret

home = str(Path.home())
script_path = os.path.realpath(__file__)

# A list of the GAM secrets that will be encrypted/decrypted.
secrets = ["oauth2.txt", "oauth2service.json", "client_secrets.json"]


def add_alias() -> None:
    """
    Adds gampass and gampass_cli to user's `.zshrc` file
    If you don't use zsh, you can change the `.zshrc` file to your liking
    """
    subprocess.Popen(r"""
    cat << EOF >> %s/.zshrc

alias gampass='python %s decrypt && gampass_encrypt &!'
alias gampass_cli='python %s $@'
gampass_encrypt()
{
while true; do
    if [[ "$(pgrep -x gam)" ]]; then
        sleep 2
    else
        python %s encrypt
        break
    fi
done
}
    """ % (home, script_path, script_path, script_path), shell=True)


def updates() -> None:
    print("\n* Go to this URL to update GAMADV-XTD3:")
    print("https://github.com/taers232c/GAMADV-XTD3/wiki/GamUpdates\n")


def sync_key() -> None:
    return setup_key(key='existing_key')


def setup_key(key=None) -> bool:
    """
    Setup a new key, write it to the gam.key file, and encrypt the secrets
    Print instructions on how to add the key to 1Password
    :return: bool
    """
    gam_path = os.path.dirname(os.path.realpath(__file__))
    gam_key = Path(f"{gam_path}/gam.key")

    if not gam_key.is_file():
        if not key:
            with open(f"{gam_path}/gam.key", "wb") as file:
                print("\n* Generating a new key...")
                key = Fernet.generate_key()
                file.write(str(key).encode())
                key = key.decode()
                add_alias()
        else:
            print("\n* Using existing key...")
            key = secret.unopass("gampass", "gamkey", "password")

        if encrypt_file(key):
            print("* Encrypted GAM secrets")
            print(f"* Added gampass as alias to {home}/.zshrc\n")
            print("Add to your 1Password account as follows:")
            print("\t[1] Open 1Password")
            print("\t[2] Create a vault named gampass")
            print("\t[3] Add/Update a new password item with the title gamkey")
            print(f"\t[4] For 'password' add/update the {key}")
            print("\t[5] You're done!")
            print("\n* Note: The gam.key file will be deleted after a successful gampass run")
            print("\033[93m* Important: Create or Update the 1Password item with the key listed above\033[0m\n")
            return True
        else:
            Path(f"{gam_path}/gam.key").unlink(missing_ok=True)
    else:
        print(f"\n* GAMpass [gam.key] file already exists: {gam_path}/\n")
        return


def encrypt_file(key=None) -> bool:
    """
    Encrypts the secret files and renames it to `file.encrypted`
    :return: bool
    """
    try:
        gam_path = os.path.dirname(os.path.realpath(__file__))

        domains_secrets = []
        for dirpath, dirnames, filenames in os.walk(gam_path):
            for file in filenames:
                if file in secrets:
                    domains_secrets.append(f"{dirpath}/{file}")
        if domains_secrets:
            if not key:
                key = secret.unopass("gampass", "gamkey", "password")

        for domainfile in domains_secrets:
            if os.path.exists(domainfile):
                f = Fernet(key)
                secret.signout(deauthorize=True)
                with open(domainfile, "rb") as file:
                    encrypted = file.read()
                encrypted = f.encrypt(encrypted)
                with open(f"{domainfile}.encrypted", "wb") as file:
                    file.write(encrypted)
                    Path(domainfile).unlink(missing_ok=True)

        if not domains_secrets:
            print("\n* No unencrypted secrets found in the GAM directory\n")
            secret.signout(deauthorize=True)
            return False
        else:
            return True

    except Exception as e:
        print(f"\n* Error: {e}")
        secret.signout(deauthorize=True)
        exit(1)


def decrypt_file() -> None:
    """
    Decrypts the encrypted secrets in the GAM directory, deletes encryption key
    :return: None
    """
    try:
        print("\n* Decrypting GAM secrets via unopass:")
        # It's using the unopass library to decrypt the credential from 1Password.
        decrypt_key = secret.unopass("gampass", "gamkey", "password")
        gam_path = os.path.dirname(os.path.realpath(__file__))
        domains_secrets = []

        for dirpath, dirnames, filenames in os.walk(gam_path):
            for files in secrets:
                path = os.path.exists(f"{dirpath}/{files}.encrypted")
                if path:
                    f = Fernet(decrypt_key)
                    with open(f"{dirpath}/{files}.encrypted", "rb") as file:
                        encrypted = file.read()
                    decrypted = f.decrypt(encrypted)
                    with open(f"{dirpath}/{files}", "wb") as file:
                        file.write(decrypted)
                        domains_secrets.append(f"{dirpath}/{files}")

        if domains_secrets:
            print(f"\033[93m* Decrypted {len(domains_secrets)//3} Google Workspace Domain!\033[0m")
            Path(f"{gam_path}/gam.key").unlink(missing_ok=True)
            print("\033[92m* Processing GAM request...\033[0m\n----------------------")
        else:
            print("\n* No encrypted secrets found in the GAM directory\n")
            secret.signout(deauthorize=True)
            exit(1)

    except Exception as e:
        print(f"\n\033[31m* Error: 1Pass key don't match!\033[0m\n---------------------------\n{e}")
        secret.signout(deauthorize=True)
        exit(1)


def help_options() -> None:
    print("Use only this to manage your GAM secrets")
    print("\nUsage: gampass_cli [option]\n")
    print("Options:")
    print("\tencrypt  \t\tEncrypt all GAM secrets")
    print("\tdecrypt  \t\tDecrypt all GAM secrets")
    print("\tsetup    \t\tSetup a key and encrypt secrets")
    print("\tupdates  \t\tView updates documentation")
    print("\tsync     \t\tEncrypt all domains with existing 1Password key")
    print("Example:")
    print("\tgampass_cli sync")
    print("\n")


def main():
    try:
        if sys.argv[1].lower() == "setup":
            setup_key()
        elif sys.argv[1].lower() == "encrypt":
            encrypt_file()
        elif sys.argv[1].lower() == "decrypt":
            decrypt_file()
        elif sys.argv[1].lower() == "sync":
            decrypt_file()
            sync_key()
        elif sys.argv[1].lower() == "update":
            updates()
        else:
            help_options()
    except IndexError:
        help_options()
        secret.signout(deauthorize=True)


if __name__ == "__main__":
    main()
