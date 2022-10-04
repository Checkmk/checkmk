# Image builder

**Not suitable for production yet**

[Packer](https://www.packer.io) is a tool to create many machine images from a single source.
We use it to build ready to use images for major cloud providers.

# How to generate images

  packer init .
  packer build checkmk.pkr.hcl

# Running the images

## qemu/kvm

  The image is located in the folder output-ubuntu-2204-amd64-qemu. The default OS user and password are ubuntu:ubuntu. Upon first login
  you are required to change your password.


# Developer Notes

Packer ships with builtin code quality tools. We recommend to run the following two commands before pushing changes.

  packer fmt .
  packer validate .
