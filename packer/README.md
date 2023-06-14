# Image builder

**Not suitable for production yet**

[Packer](https://www.packer.io) is a tool to create many machine images from a single source.
We use it to build ready to use images for major cloud providers.

# How to generate images

To generate an image first you need to initialize packer and download all required plugins with

  packer init .

Afterwards you can build the images. The builds depends on a few secrets that are defined as variables.
We recommend you create a build.sh script that sets all variables for you. Have a look at the example\_build.sh file.
For local development we recommend to only run the qemu builder

  ./build.sh -only="checkmk-ansible.qemu.builder" .

Since the build definitions are split across multiple files you have to run the build on the current folder ".". Just
specifying one file will lead to an error.


# Running the images

## qemu/kvm

  The image is located in the folder output-ubuntu-2204-amd64-qemu. The default OS user and password are ubuntu:ubuntu. Upon first login
  you are required to change your password.


# Developer Notes

Packer ships with builtin code quality tools. We recommend to run the following two commands before pushing changes.

  packer fmt .
  packer validate .
