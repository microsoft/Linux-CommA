# Linux Commit Analyzer (CommA)

[![Build Status](https://dev.azure.com/ms/Linux-CommA/_apis/build/status/microsoft.Linux-CommA?branchName=main)](https://dev.azure.com/ms/Linux-CommA/_build/latest?definitionId=366&branchName=main)

This tool populates a database with the details of which patches that are
upstream (in `linux-mainline`) are missing from distros in their downstream
kernels (e.g. Ubuntu kernels). For our use case, we are looking at Hyper-V
patches and checking downstream azure specific kernels, but this is adaptable.

## Getting Started

### Install Dependencies

Setup [Microsoft SQL
repos](https://docs.microsoft.com/en-us/sql/linux/quickstart-install-connect-ubuntu?view=sql-server-ver15#tools)
(this is for `mssql-tools`):

> Caution: these commands use `sudo` and add a package repository. Change the
> Ubuntu version to your version (`cat /etc/os-release` for the number).

```sh
. /etc/os-release
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/${VERSION_ID}/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
```

Install the required packages for connecting to the Microsoft SQL database:

```sh
sudo apt update
sudo apt install mssql-tools unixodbc-dev
```

For the symbol matcher, install `exuberant-ctags` as the default `ctags` will
not work:

```sh
apt install exuberant-ctags
```

### Install CommA

```sh
pip install .
```

### Running CommA

1. Provide the URL to the secrets repo with `export
   COMMA_SECRETS_URL=<URL/to/secrets/repo>`.
2. Run `comma run --upstream --downstream`

This will parse the upstream and downstream repos.

### Setting Up Secrets

Place database info into the following environment variables before running CommA:
COMMA_DB_URL
COMMA_DB_NAME
COMMA_DB_USERNAME
COMMA_DB_PW

>[!TIP]
> We leave it to the user to keep their secrets secure before running CommA. Azure Pipelines provides a few mechanisms for managing secrets, use a comparable tool when creating a CommA pipeline to ensure you don't leak your database credentials.


## Contributing

This project welcomes contributions and suggestions. Most contributions require
you to agree to a Contributor License Agreement (CLA) declaring that you have
the right to, and actually do, grant us the rights to use your contribution. For
details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether
you need to provide a CLA and decorate the PR appropriately (e.g., status check,
comment). Simply follow the instructions provided by the bot. You will only need
to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of
Conduct](https://opensource.microsoft.com/codeofconduct/). For more information
see the [Code of Conduct
FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact
[opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional
questions or comments.

## Legal Notices

Microsoft and any contributors grant you a license to the Microsoft
documentation and other content in this repository under the [Creative Commons
Attribution 4.0 International Public
License](https://creativecommons.org/licenses/by/4.0/legalcode), see the
[LICENSE-DOCS](LICENSE-DOCS.md) file, and grant you a license to any code in the
repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE](LICENSE.md) file.

Microsoft, Windows, Microsoft Azure and/or other Microsoft products and services
referenced in the documentation may be either trademarks or registered
trademarks of Microsoft in the United States and/or other countries. The
licenses for this project do not grant you rights to use any Microsoft names,
logos, or trademarks. Microsoft's general trademark guidelines can be found at
http://go.microsoft.com/fwlink/?LinkID=254653.

Privacy information can be found at https://privacy.microsoft.com/en-us/

Microsoft and any contributors reserve all other rights, whether under their
respective copyrights, patents, or trademarks, whether by implication, estoppel
or otherwise.
