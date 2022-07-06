import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from unopass import unopass as secret

home = str(Path.home())
gam_path = os.path.dirname(sys.argv[0])
script_path = os.path.realpath(__file__)

# A list of the secrets that will be encrypted.
secrets = ["client_secrets.json", "oauth2service.json", "oauth2.txt"]

# It's using the unopass library to decrypt the credential from 1Password.
decrypt_key = secret.unopass("gampass", "gam", "credential")


def add_alias() -> None:
    """
    Adds gampass as an alias to the user's `.zshrc` file & sources the file
    """
    alias = f"alias gampass='f(){{ python {script_path} decrypt && gam \"\$@\" ; python {script_path} encrypt;  unset -f f; }}; f'"
    os.system(f'echo "{alias}" >> {home}/.zshrc')
    os.system(f"source {home}/.zshrc > /dev/null 2>&1")


def generate_key() -> str:
    """
    If the gam.key file doesn't exist, generate a new key, write it to the gam.key file, and encrypt the secrets
    Print instructions on how to add the key to 1Password
    :return: The key is being returned.
    """
    gam_path = os.path.dirname(os.path.realpath(__file__))
    gam_key = Path(f"{gam_path}/gam.key")
    if not gam_key.is_file():
        add_alias()
        print("\n* Generating GAMpass encryption Key")
        key = Fernet.generate_key()
        with open(f"{gam_path}/gam.key", "wb") as file:
            file.write(key)
            add_alias()
            encrypt_file()
            print("* GAMpass encryption Key generated")
            print("* Encrypted GAM secrets")
            print(f"* Added gampass as alias to {home}/.zshrc\n")
            print("Add to your 1Password account as follows:")
            print("\t[1] Open 1Password")
            print("\t[2] Create a vault named gampass")
            print("\t[3] Add a new PASSWORD item with the title gam")
            print(f"\t[4] For 'credential' add {key.decode()}")
            print("\t[5] You're done!")
            print("\nNote: gam.key will be deleted on successful gampass first run")
            print(
                "Note: If these are updated GCP secrets, update the 1Password gampass item with new key\n"
            )
            return key
    else:
        print(f"\nGAM [gam.key] file already exists: {gam_path}/\n")
        return


def encrypt_file() -> None:
    """
    It encrypts the secret files and renames it to `file.encrypted`
    :return: None
    """
    gam_path = os.path.dirname(os.path.realpath(__file__))
    for files in secrets:
        path = Path(f"{gam_path}/{files}")
        if path.is_file():
            f = Fernet(decrypt_key)
            with open(f"{gam_path}/{files}", "rb") as file:
                encrypted = file.read()
            encrypted = f.encrypt(encrypted)
            with open(f"{gam_path}/{files}.encrypted", "wb") as file:
                file.write(encrypted)
                Path(path).unlink(missing_ok=True)
                secret.signout(deauthorize=True)
        else:
            print(f"\nGAM unencrypted secrets not found in {gam_path}/:\n{secrets}\n")
            secret.signout(deauthorize=True)
            return


def decrypt_file() -> None:
    """
    It decrypts the encrypted secrets in the GAM directory, deletes encryption key
    :return: None
    """
    print("\nDecrypting GAM secrets via unopass:")
    gam_path = os.path.dirname(os.path.realpath(__file__))
    for files in secrets:
        path = Path(f"{gam_path}/{files}.encrypted")
        if path.is_file():
            f = Fernet(decrypt_key)
            with open(f"{gam_path}/{files}.encrypted", "rb") as file:
                encrypted = file.read()
            decrypted = f.decrypt(encrypted)
            with open(f"{gam_path}/{files}", "wb") as file:
                file.write(decrypted)
            print(f"Decrypted: {files}")
        else:
            print(f"\nGAM encrypted .encrypted secrets not found in {gam_path}/\n")
            return
    Path(f"{gam_path}/gam.key").unlink(missing_ok=True)
    print("Processing GAM request...\n----------------------\n")


def help_options() -> None:
    print("\nUsage: python gampass.py [option]\n")
    print("Options:")
    print("\tgenerate\tGenerate a key & encrypt secrets")
    print("\tencrypt\t\tEncrypt GAM files")
    print("\tdecrypt\t\tDecrypt GAM files")
    print("\n")
    print("Example:")
    print("\tpython gampass.py generate")
    print("\tpython gampass.py encrypt")
    print("\tpython gampass.py decrypt")
    print("\n")


def main():
    """
    It checks the first argument passed to the script and calls the appropriate function
    """
    try:
        if sys.argv[1].lower() == "generate":
            generate_key()
        elif sys.argv[1].lower() == "encrypt":
            encrypt_file()
        elif sys.argv[1].lower() == "decrypt":
            decrypt_file()
        else:
            help_options()
    except IndexError:
        help_options()
        secret.signout(deauthorize=True)


if __name__ == "__main__":
    main()
