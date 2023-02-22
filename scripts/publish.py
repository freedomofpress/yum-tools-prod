#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import json
import tempfile

RPM_DIR = "dangerzone"


def import_key(key_id, db_path):
    try:
        key = subprocess.check_output(["gpg", "--export", "--armor", key_id])
    except subprocess.CalledProcessError as e:
        fail(f"Error fetching key '{id}': {e}")

    with tempfile.NamedTemporaryFile() as f:
        f.write(key)
        f.flush()
        try:
            subprocess.check_call([
                "rpmkeys", "--dbpath", db_path, "--import", f.name
            ])
        except subprocess.CalledProcessError as e:
            fail(f"Error importing key: {e}")


def verify_sig_rpm(path, key_id):
    print(f">> Verifying {path}")
    try:
        # Since we can't specify with which key to check sigs, we should create
        # a new keyring.
        with tempfile.TemporaryDirectory() as db_path:
            import_key(key_id, db_path)
            output = subprocess.check_output([
                "rpm", "--dbpath", db_path, "--checksig", path
            ])
        # rpm --checksig returns 0 if there is *no* signature. I couldn't
        # find a way other than parsing stdout
        # NOTE: See also
        # https://hussainaliakbar.github.io/signing-and-verifying-rpm-packages/
        line = output.decode("utf-8").rstrip()
        expected_output = "{}: digests signatures OK".format(path)
        if line != expected_output:
            fail(f"Signature verification failed for {path}")
        else:
            print(line)
    except subprocess.CalledProcessError as e:
        fail("Error checking signature: {}".format(str(e)))


def verify_all_rpms(key_id):
    for root, dirs, files in os.walk(RPM_DIR):
        for name in files:
            path = os.path.join(root, name)
            verify_sig_rpm(path, key_id)


def sign_rpm(path, key_id):
    # NOTE: Taken from
    # https://hussainaliakbar.github.io/signing-and-verifying-rpm-packages/
    print(f">> Signing {path}")
    try:
        subprocess.check_call([
            "rpm", "--define", f"_gpg_name {key_id}", "--addsign", path,
        ])
    except subprocess.CalledProcessError as e:
        fail(f"Error signing package {path}: {e}")


def sign_all_rpms(key_id):
    for root, dirs, files in os.walk(RPM_DIR):
        for name in files:
            path = os.path.join(root, name)
            sign_rpm(path, key_id)


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", default=False)
    parser.add_argument("--sign", action="store_true", default=False)
    parser.add_argument("--all", action="store_true", default=False)
    parser.add_argument(
        "--key-id",
        type=str,
        help="The key ID that will be used",
        default="FPF Packages TESTING key <sysadmin@freedom.press>"
    )
    parser.add_argument("packages", type=str, nargs="*", help="Files to sign/verify")
    args = parser.parse_args()

    # Fail if no package is specified or not using '--all'
    if not args.all and not args.packages:
        fail("Please specify an rpm package or --all")

    if args.verify:
        if args.all:
            verify_all_rpms(args.key_id)
        else:
            for package in args.packages:
                assert os.path.exists(package)
                verify_sig_rpm(package, args.key_id)
    elif args.sign:
        if args.all:
            sign_all_rpms(args.key_id)
        else:
            for package in args.packages:
                assert os.path.exists(package)
                sign_rpm(package, args.key_id)
    else:
        fail("Please use the --verify or the --sign option")


if __name__ == "__main__":
    main()
