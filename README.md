# Triforce Link #

This is a simple application that creates a mapping.csv file which maps power plants from 3 different data sources:

1. ENTSO
2. Platts
3. GPPD

These data come in the form of CSV files and by default located in data/ directory with the names entso.csv, platts.csv, and gppd.csv.
However, this application provides you with the option to pass an arbitrary file using certain CLI parameters (all of which are optional).

The mapping algorithm goes as follows:
1. (Optional) Pre-process / Normalize Power Plant Names - uses the plant_names of ENTSO as the reference to do fuzzy matching to both Platts and GPPD.
    For all matches that pass a certain WRatio score (90), it replaces the plant_names in Platts and GPPD with the reference name from ENTSO, effectively "normalizing"
    the names for later queries/mapping. This increases the processing time quite a bit and so I opted to disable this by default, but simply setting a
    parameter (-n True) to the command call will enable this. The given test data benefits with only 2 additional mapping found because of this but other datasets
    may be able to benefit more.
2. Phase 1 - Map ENTSO-GPPD-Platts using plant name, country, and fuel type. 
    - Depending on whether step 1 ran (normalized power plant names), the plant_name matching will either employ fuzzy matching (effectively) or just a basic substring match
3. Phase 2 - Create temporary dataframes/tables based on platts_plant_id mapping of GPPD and Platts, then use that to replace nulls in Phase 1 (ie. power plants it wasn't able to map).


## Libraries required (pre-provisioned)

This application utilizes the following libraries/technologies:

- Pandas = for all data processing
- Padasql = for SQL access to dataframes/tables
- Fuzzywuzzy = for fuzzy matching (ex. using WRatio scorer)
- Pytest = for unit testing

> The docker container this application comes in with should already provision necessary installations. See **Dockerfile**.
>
> As such, the only real requirement is that you have the **docker engine**.

## Running the application

There are two ways to run this application, in the order of preference:

### Run using the pre-built docker image

There is a pre-built docker image in Dockerhub ( **gadm01/triforce-link** ) - which means you don't even need to pull this repository. In a command line run the following:

```bash  
#Pull the docker image
docker pull gadm01/triforce-link

#Run the docker container
docker run --detach --name triforce-link -it gadm01/triforce-link

#Go inside the container's shell to run the CLI of triforce-link
docker exec -ti triforce-link bash
```

Once you're inside the container, everything will be provisioned for you so you can simply use triforce-link's CLI. Here are sample commands:

```bash  
#Navigate to triforce-link's root directory:
cd /home/triforce
#Run the mapper with all default values. NOTE: This will not do any fuzzy matching but this is the fastest (3-5 seconds on default datasets)
python3 mapping.py

#Run the mapper with fuzzy matching turned ON. This will be slower but has the potential to map more power plants (~3 mins on default datasets)
python3 mapping.py -n True

#Run the mapper with more verbosity
python3 mapping.py -n True -v

#Print usage help
python3 mapping.py -h
```

### Run by building from source (ie. docker build)

If you really want to build from source, here are the steps:

```bash  
#Make sure you are in the same directory as the Dockerfile, then run
docker build -t triforce-link .

#Run the docker container
docker run --detach --name triforce-link -it triforce-link

#Go inside the container's shell to run the CLI of triforce-link
docker exec -ti triforce-link bash
```
Once you're inside the container, you can use triforce-link's CLI as shown in the previous section.

## Running the tests

Assuming all steps before this section was successful, you can simply run pytest to run all unit tests:

```bash  
#Go to application's home
cd /home/triforce
#To run all tests:
python3 -m pytest
#To run all tests with the name of the tests and better printings:
python3 -m pytest -v
#To run specific test, invalid_gppd_file test for example:
python3 -m pytest -v -k test_map_data_invalid_gppd_file
```

### Areas of improvement
- More unit tests and integration tests
- Different datasets (ex. more ENTSO rows)

### Questions/Clarifications ###
Please contact:

* **Kevin Palis** <kevin.palis@gmail.com>