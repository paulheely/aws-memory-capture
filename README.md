# Virtual Environment
I use a virtual environment for my Python development and code exectution. To setup and active the `env` run the following commands in the project base directory.
These work on a Windows system with Python3 installed via scoop. Adjust for your system as needed.

```
python -m env env
env\Scripts\activate
``` 

# Install required packages
```
pip install -r requirements.txt
```

# Pre-Reqs
- The current script is written to work with [Belkasoft RAM Capturer](https://belkasoft.com/ram-capturer).
- The target machine must allow SSM Run Command
- The ROLE specified for the temp workstation must allow full S3 access and SSM Run Command.

# Script Execution
```
usage: capture.py [-h] [--profile PROFILE] [--region REGION] [--toolzip TOOLZIP] [--targetid TARGETID] [--role ROLE]
                  [--workami WORKAMI] [--outputfile OUTPUTFILE]

options:
  -h, --help            show this help message and exit
  --profile PROFILE, -p PROFILE
                        AWS profile
  --region REGION, -r REGION
                        AWS region
  --toolzip TOOLZIP, -t TOOLZIP
                        Memory Capture tool zip file
  --targetid TARGETID, -i TARGETID
                        ID of the target machine.
  --role ROLE, -l ROLE  Role to attach to TempWorkstation
  --workami WORKAMI, -a WORKAMI
                        AMI to use for TempWorkstation
  --outputfile OUTPUTFILE, -o- OUTPUTFILE
                        Output file name
```