# Scenario 1 - Because One Service Was Too Boring

## How long will this take?
Depending on your experience and knowledge about the covered topics **this scenario should take between 1 to 2 hours to complete**.

## TL;DR - what you'll learn and what we'll use
### GCP Services Used:
- Cloud Build (with Buildpacks)
- Cloud Run (backend)
- Cloud Functions (async processing)
- Pub/Sub
- Cloud SQL (Postgres)

### What you will learn
- How to deploy serverless applications to Cloud Run & Cloud Functions
- How to connect GCP-managed services to resources inside your own VPC (spoiler: it’s not as magical as marketing suggests)
- How to build a secure, end-to-end serverless microservice architecture
- How to apply Principle of Least Privilege (PoLP) to serverless components
- How to avoid Dockerfiles using Buildpacks, reducing ops overhead
- And finally how to tie this all together

## The task at hand
You are tasked with deploying the new up and coming Hello Game App which apparently is destined for success. You worked hard with the architects and developers and decided on a **fully managed and serverless** deployment on GCP. The goal of this excercise is to deploy a fully functional (and by functional I mean working) microservice application using **Cloud Run, Cloud Functions, Pub/Sub and Cloud SQL**. As a bonus we will also use **Buildpacks** as our build provider to deploy without working on the Dockerfiles - we are reducing the operational overhead as much as we can. We will also explore the implementation of principle of least privilege, and learn how to connect these managed services together while keeping all of the traffic (except for the app frontend) safely inside the GCP internal network. Spoiler alert: this last requirement (internal backend traffic) will come to bite us more than once - we'll reveal the problems as we go.

## How to work with this scenario
I will provide explanations with what, why and how to do it in the correct order. Each of the resource will come with a gcloud cli command for it's creation. I will also provide a script that will confirm the completion of each of the sections (if the script is not there this means I forgot about it). The commands will be hidden by default and I highly encourage you to think of your own implementation before checking and/or running them. You are free to work from the Cloud Shell or Cloud Console, whatever suits your learning style the best (the less experienced you are with GCP the more I would personally lean towards the Cloud Console). However keep in mind that the provided checkpoint scripts will only work if you stick with my naming conventions.

# Instructions
We are going to tackle this scenario on sort of a layer basis, provisioning resources layer by layer while keeping in mind their dependencies. This should help you understand which resources and settings depend on which other resources and how to design a GCP system from the ground up. Here's the target setup we're aiming for:
![Architecture Overview](assets/scenario-1-architecture.png "Hello Game App Architecture")

> ## ❗ Important Note
> This scenario includes a bash script that will verify your progress at the end of each of the tasks. This script assumes the same naming conventions I'll be using throughout the tutorial. You can do your own thing, but be advised that the script will not work if you choose to do so. The script is located in the root folder of this scenario (`scenarios/1/check-resources.sh`). The **resources are named on the architecture graph**, but **I will also remind my names throughout** the tutorial when we create the resources.

## Task 0 - Set up your project and enable required APIs
First things first - as this is a new project for our organization, you guessed it - we need to create it. Head over to your tool of choice and provision a new GCP project. As stated above I will be using the gcloud CLI for all commands, so here are the commands to create a new project and set it as your default one.
<details>
<summary>gcloud commands for creating and setting up a new project</summary>

NOTE: I am omitting the project ID - if it is not provided, gcloud will generate a random one for you (like in the example below). This has to be globally unique if you want to set it yourself:
```bash
# Set your desired project name
export PROJECT_NAME="hello-game-app"

# Create a new GCP project
gcloud projects create --name $PROJECT_NAME
No project ID provided.

Use [hello-game-app-477717] as project ID (Y/n)?
```

```bash
# Get the project id and save it to an env variable for future use
export PROJECT_ID=$(gcloud projects list --filter="name:$PROJECT_NAME" --format="value(projectId)")

# Set the newly created project as the default one
gcloud config set project $PROJECT_ID
```
</details>  

> ### ❗ A note on billing and budgets
> Now this part is very specific to your account, so I would suggest going to the Cloud Console -> Billing -> Budgets and alerts and setting up a budget for this project, just in case you forget to delete the project or some cost accumulating resources after you're done with the scenario. Most of the services we're going to use have a free tier that we're highly unlikely to exceed, but we will have to pay for our database setup. A budget of $5 should be more than enough - **I've spent around $1** running this scenario and I took quite a bit of extra time to work on it in the meantime.  

<details>
<summary>gcloud commands for setting up a budget</summary>
We will also enable our first API here - the Cloud Billing API, as it's required to set up budgets via gcloud CLI.

```bash
# List your billing accounts
gcloud billing accounts list

# Link the billing account to your project
gcloud billing projects link $PROJECT_ID --billing-account=YOUR_BILLING

# Create a budget for your project (adjust the amount as needed)
# This example creates a budget of $5 (or another default currency) with alerts at 50%, 90% and 100%
# and links it to your project
gcloud billing budgets create --billing-account "YOUR_BILLING" \
 --display-name "Hello Game App Budget" \
 --budget-amount 5 \
 --threshold-rule percent=0.5 \
 --threshold-rule percent=0.9 \
 --threshold-rule percent=1.0 \
 --project $PROJECT_ID
```
</details>

And finally for the APIs... we will unlock these as we go, so that you can get a better understanding of what services are under which APIs. The Cloud Console should enable these for you automatically when you try to create a resource that depends on a disabled API. The gcloud CLI will walk you through the process if you try to use a disabled API. Let's move on to our foundations.

## Task 0,5 - Download the scenario repository with the application code
This scenario was prepared to be run-able from the Cloud Shell. If you choose to run this on your machine, and for some reason it doesn't work, there is only one thing I can say: *it works on my machine*. Jokes aside, I guarantee that it will work on Cloud Shell. To download the repository to your Cloud Shell environment, run the following commands:
```bash
git clone https://github.com/brzezinskilukasz/gcp-tutorials.git

# Move to the scenario folder
cd gcp-tutorials/scenarios/1/
```

And without further ado, let's get to work. 👷

## Task 1 - First layer: independent resources
Time to get our hands dirty. And by dirty I really mean clean, as we're going to go "by the books" and set up a clean foundation for our application. After this step we will be ready to start deploying. First, we need dedicated Service Accounts for each component. As per best practices, each service should run under its own identity so we can apply fine-grained permissions. Press the arrow to expand the gcloud commands. Oh and by the way, something that grinds my gears - this is not the year 1980, we have enough space available - please name your resources in a descriptive manner instead of using random strings of characters or abbreviations that confuse everyone (including you, couple years forward when you're subbing in for a colleague on sick leave in a project that you created and since moved on).  

The service accounts we need are:  
✅ **hello-frontend-sa** - for the Cloud Run frontend service  
✅ **hello-backend-sa** - for the Cloud Run backend service  
✅ **hello-function-sa** - for the Cloud Functions function
<details>
<summary>gcloud commands for creating service accounts</summary>

```bash
# Create service account for Hello Game Frontend (Cloud Run)
gcloud iam service-accounts create hello-frontend-sa \
    --description="Service account for Hello Game Frontend (Cloud Run)" \
    --display-name="hello-frontend-sa"
```

```bash
# Create service account for Hello Game Backend (Cloud Run)
gcloud iam service-accounts create hello-backend-sa \
    --description="Service account for Hello Game Backend (Cloud Run)" \
    --display-name="hello-backend-sa"
```

```bash
# Create service account for Hello Game Function (Cloud Functions)
gcloud iam service-accounts create hello-function-sa \
    --description="Service account for Hello Game Function (Cloud Functions)" \
    --display-name="hello-function-sa"
```
</details>  
  
This is as far as we can go regarding IAM, at least for now. Yes, we could assign roles at the project level immediately, but that would overshoot and violate the principle of least privilege. Once the services exist, we’ll scope roles only to the specific resources they must access (e.g., Pub/Sub topic, Cloud SQL, invoking specific Cloud Run service). That’s when we’ll return to IAM.

Next we need a VPC - even though we're relying solely on managed services we will still need it for our Cloud SQL instance - more on that later. For now just create a simple VPC in custom subnet mode and subnet in europe-central2 region (or any other one you fancy, just make sure to adjust the rest of the commands accordingly). Oh and remember to use descriptive names for your resources, please don't name this hga-vpc (what does that mean? well go back to my previous naming rant) or something like that.  

The resource names I'll be using are:  
✅ **hello-game-vpc** - the VPC network  
✅ **hello-game-subnet** - the subnet

<details>
<summary>gcloud commands for creating VPC and subnet</summary>
Another API we need to enable here is the Compute Engine API, as VPCs are part of it.
Also there is an important choice we have to make here.

```bash
# Create VPC
gcloud compute networks create hello-game-vpc \
    --subnet-mode=custom

# As we'll shortly commit to a region where our app will be deployed, for our ease let's save it to an env variable
# Keep in mind to adjust the region if you decide to go with another one - the example below uses my region of choice
export REGION="europe-central2"

# Create subnet
gcloud compute networks subnets create hello-game-subnet \
    --network=hello-game-vpc \
    --region=$REGION \
    --range=10.0.0.0/24
```
</details>

And finally we can create our Pub/Sub topic that will be used to trigger the backend function. To be honest, this could be done later but creating it now falls well within our flow so let's do it.  
The resource name I'll be using is:  
✅ **hello-game-submissions** - the Pub/Sub topic  
<details>
<summary>gcloud commands for creating Pub/Sub topic</summary>

```bash
# Create Pub/Sub topic
gcloud pubsub topics create hello-game-submissions
```
</details>

🎉 **Congratulations!** You've successfully laid the foundation for your serverless architecture! 

This concludes the first layer of our setup - think of it as building a solid foundation before constructing the house. Before we move on to the exciting part (deploying our applications), let's make sure everything is in place.

### What you should have at this point:
✅ **3 Service Accounts** - Each with their own identity for security best practices  
✅ **1 VPC Network** - Your private network playground  
✅ **1 Subnet** - The neighborhood where your resources will live  
✅ **1 Pub/Sub Topic** - Your messaging highway for async communication  

### 🔍 **Checkpoint Time!**
Let's run our verification script to make sure everything is properly configured. Keep in mind that the script assumes you have named your resources exactly as specified above:

```bash
# Make the script executable (if you haven't already)
chmod +x ./check-resources.sh

# Run the Task 1 verification
./check-resources.sh task-1
```

If you see **"All checks passed! (6/6)"** - you're golden! 🌟  
If not, don't worry - the script will tell you exactly what's missing so you can fix it before continuing.

## A note on the upcoming layering strategy
Next we will be deploying our components, going from the back (the DB) all the way to the front (the frontend). We will prepare everything to be ready to go before deploying the next (or rather previous) component, but we will deliberately **not assing the required IAM roles** right off the bat. This will allow us to better see how these premissions are required for each of the components to start functioning and also it will help us make sure that these roles are actually meaningful and are doing their purpose.

## Task 2 - Second layer: we start deploying
We've set up a proper building foundation for a safe deployment, time to put it to work. There are two ways to go about this:
- deploy the application without any restrictions - this is good for a PoC or maybe a test deployment, to make sure the application actually works, and it's not the permissions that are breaking it
- deploy the application to a fully restricted environment and enable only the required traffic - as we've already ran the tests and know that our app works that's what we'll do. Also it is much better for our tutorial as we will see exactly what needs to be "unlocked" to enable the safe traffic

So keep in mind that while our services should start (as this is a modern, very well built, cloud-native application, we expect a *graceful degradation* of services) they might not be operational.

Now, while the order of provisioning resources doesn't really matter at this stage, since the parts of the application will not be able to connect to each other due to missing permissions, it makes sense to work backwards - from the database, as our backend needs the database connection information, and our frontend needs the backend URL. So let's start with the database.

### Deploying and preparing the Cloud SQL Instance
Now things are about to get interesting. Our requirement is to **keep all of the traffic internal**. However Cloud SQL is a managed service, and as such it doesn't live inside our VPC by default. To connect to it privately we will need to set up **Private Service Access**. This requires us to reserve an IP range for the service networking, and then create the Cloud SQL instance with private IP enabled. Let's go through the steps one by one (make sure to adjust the region if you decided to go with another one). This is actually much more user-friendly when done through the Cloud Console - when you check the Private IP box the wizard will guide you through the creation of these resources. But as I am going gcloud-only here are the commands:

<details>
<summary>gcloud commands preparing for creation of Cloud SQL instance with private IP</summary>

```bash
# Set env variables to not mess up (most of these should already be set from previous steps)
export REGION="europe-central2"
export PROJECT_ID=$(gcloud config get-value project)
export NETWORK="hello-game-vpc" 
export SUBNET="hello-game-subnet"
```

```bash
# Create a private VPC peering connection (required before private CloudSQL can be created)
# The database services use a specific range of IPs that we need to reserve first
gcloud compute addresses create google-managed-services-$NETWORK \
  --global \
  --purpose VPC_PEERING \
  --prefix-length 16 \
  --network $NETWORK

# Establish the VPC peering connection between our VPC and the Cloud SQL service
gcloud services vpc-peerings connect \
  --service servicenetworking.googleapis.com \
  --network $NETWORK \
  --ranges google-managed-services-$NETWORK
```

</details>

And now for the database. The important parts are:  
✅ No public IP  
✅ Private IP enabled  
✅ Cloud SQL instance inside our VPC  
✅ IAM Authentication enabled (we will use this to avoid storing passwords/secrets) (Flags section)  
Other parameters are up to you. The command below spawns a IAM Authentication enabled Postgres 17 instance with minimal specs, the selected flags (options) explaination is below the command in the hidden section.

<details>
<summary>gcloud command for creating the Cloud SQL instance</summary>

```bash
gcloud sql instances create hello-game-db \
  --database-version POSTGRES_17 \
  --edition enterprise \
  --tier db-f1-micro \
  --region $REGION \
  --network $NETWORK \
  --no-assign-ip \
  --availability-type ZONAL \
  --storage-size 10GB \
  --storage-type SSD \
  --database-flags cloudsql.iam_authentication=on \
  --root-password "SafePassword123!"  # we need this to set up SAs privileges later
```

Flags explanation:  
`--database-version`, `--edition`, `--tier`, `--storage-size`, `--storage-type`, `--availability-type`, `--region` - these are standard DB options for Cloud SQL, nothing fancy, I am going for the most budget friendly setup I could find.

`--network` - the VPC network that this instance will connect to. This is required for Private IP. It works in tandem with the Private Service Access (VPC Peering) we set up earlier to assign an IP from our reserved range to the database instance, making it accessible from our VPC.  

`--no-assign-ip` - disables **public** IP assignment; this is crucial for our requirement of keeping all traffic internal  

`--database-flags cloudsql.iam_authentication=on` - enables IAM Database Authentication; this allows us to use GCP IAM identities to authenticate to the database instead of traditional username/password pairs  

`--root-password` - we need to set a root password here, as we will need it later to set up the database users and their privileges; however we won't be using it for application access, as we'll be using IAM DB Auth for that
</details>

> ## ⏳ Warning
> This configuration takes quite a bit of time to provision, and if you plan to take a break and stop it, it will also take quite a bit of time to start again. If you're impatient consider provisioning a stronger machine.

Now we have to create our database and the users. Since we will be using IAM DB Authentication we need to create database accounts for our service accounts. This authentication method ties the database user to GCP IAM identity automatically, in a following way (also look at the architecture overview): 

| GCP Service Account                                    | Database User                      | User Type                     |
|--------------------------------------------------------|------------------------------------|-------------------------------|
| hello-backend-sa@<PROJECT_ID>.iam.gserviceaccount.com  | hello-backend-sa@<PROJECT_ID>.iam  | cloud_iam_service_account     |
| hello-function-sa@<PROJECT_ID>.iam.gserviceaccount.com | hello-function-sa@<PROJECT_ID>.iam | cloud_iam_service_account     |

> ## ⚠️ Note
> Note the differences in the syntax between GCP Service Account and Database User. The database user omits the `.gserviceaccount.com` suffix. This is due to username length limitations in the database.

And assign them the required privileges to operate the database.
You can read more on managing the IAM db users [here](https://docs.cloud.google.com/sql/docs/postgres/add-manage-iam-users)

<details>
<summary>gcloud commands for creating database, users and assigning roles</summary>

``` bash
# Create the database
gcloud sql databases create hello-game-submissions-db \
  --instance=hello-game-db

# Create the database users for backend and function service accounts
gcloud sql users create hello-backend-sa@$PROJECT_ID.iam \
  --instance=hello-game-db \
  --type=cloud_iam_service_account # <- this signifies that this is an IAM-authenticated user

gcloud sql users create hello-function-sa@$PROJECT_ID.iam \
  --instance=hello-game-db \
  --type=cloud_iam_service_account
```
</details>

And now we are in a little bit of a pickle. We have to assign the required privileges to our service accounts, so that they can operate on the database (for example run the initial db migration). However the instance is in a private network, so we can't connect to it from our local machine (unless we are in a VPN connected to the VPC, but that's an unlikely scenario, especially for our requirements). Cloud Shell can't connect to it either. We could run a job to do that, but... as per our requirements we have to use IAM DB Auth for programatic access, and this would not have any permissions on that database itself. Talk about reducing overhead by running managed services... So the only viable option here is to create a temporary 'bastion' VM inside our VPC, connect to it via SSH and run the required commands from there. Alternatively we could create a script, upload it to the Cloud Storage bucket and then finally import it to our database using the `gcloud sql import` command. But we don't have a bucket. Problems, problems...

...but wait - being an **automation first** enthusiast saying this pains me a little - but Cloud Console to the rescue. Even though we can't connect to the database from Cloud Shell, let's explore this neat feature that will let us into the database. In the Cloud Console to go the Cloud SQL -> Instances -> hello-game-db. Then from the menu on the left select **Cloud SQL Studio**. In the pop-up window select the newly created database and login using username `postgres` and the password we set while creating the instance with the `--root-password` flag. We are now connected to our database instance. One more tweak to do, we have to adjust the SA usernames, the script provided in this scenario has placeholders:
```sql
GRANT SELECT ON game_submissions TO "hello-backend-sa@project_id_placeholder.iam";
```

for the project ID, so we have to replace them with our actual project ID. Run this command to replace the placeholders in the SQL file:
```bash
sed -i "s/project_id_placeholder/$PROJECT_ID/g" ~/gcp-tutorials/hello-game-app/database_setup.sql
```

Once inside, open the **Query Editor** tab and paste the contents of the `database_setup.sql`. Run the script and voila - our database is ready to go. Simple, wasn't it? And we're only just getting started... Remember, we'll be doing this manually just this one time. </i>(Narrator: It became the permanent deployment process for the next 4 years)</i>

🎉 **Congratulations!** You've successfully set up a fully private Cloud SQL database instance and we even managed to miraculously connect to it!

### What you should have at this point:
✅ **1 Cloud SQL Instance** - Your managed database server  
✅ **1 Database** - The heart of your application data  
✅ **2 Database Users** - Secure access for your backend and function  
✅ **Database graded roles** - Proper permissions for database operations  


### 🔍 **Checkpoint Time!**
Let's run our verification script to make sure everything is properly configured. Keep in mind that the script assumes you have named your resources exactly as specified above:

```bash
# Make the script executable (if you haven't already)
chmod +x ./check-resources.sh

# Run the Task 2 verification
./check-resources.sh task-2
```
If you see **"All checks passed! (6/6)"** - you're golden (again)! 🌟

## Task 3 - Third layer part 1: deploying the backend service
### Deploying the Cloud Run Backend... or are we?
Let's keep the momentum going and deploy the backend service. But... surprise. We've just locked our Cloud SQL instance inside of our private VPC. Cloud Run, being another managed service runs in the Google-managed infrastructure and can't access our VPC by default. Is Google trying to make our lives difficult? Actually, as of not so long ago, no. In the olden days (read: 2023/2024) we would have to provision a pricey service called **Serverless VPC Access Connector**, which was a set of VMs that would provide an interface between the managed services and our VPC. Beware of this resource, as this is a legacy feature that is kept for backwards compatibility reasons and accumulate costs even when idling.

#### Enter the Direct VPC egress
With the addition of **Direct VPC egress** for Cloud Run and Cloud Functions (gen 2) and its release to general availability this task has gotten quite a bit simpler and is a matter of just a couple extra flags during the deployment:
- `--network` - the VPC network name
- `--subnet` - the subnet name
- `--vpc-egress` - the type of egress; in our case `all-traffic` to route all outbound traffic through the VPC

> #### How it works 💡
> The way it works is actually quite subtle - it attaches the network interface (NIC) directly to the container instance. Therefore as the containers scale to 0 so do the NICs - reducing the operational cost of this as compared to the legacy option. 
> #### Important Note ⚠️
>The **Direct VPC egress** reserves a set of IPs in your VPC subnet and it requires the subnet to have an address range of at least /26 or larger. For highly scaling workloads consider reserving a larger range to accommodate the scaling needs.

This is not something you provision, it's just a set of configuration options that tell Cloud Run to route all of its traffic through the VPC.

This is exactly what we need to connect to our private Cloud SQL instance:

### Actually deploying the Cloud Run Backend
Go to the backend source code folder
```bash
cd ~/gcp-tutorials/hello-game-app/hello-backend/
ls -la
ls src -la
```
and review what's in there. Note that we are to deploy a containerized application but there is no Dockerfile in sight. As a bonus in this tutorial we will use **Buildpacks** to build our container images to reduce the operational overhead of maintaining Dockerfiles (because reducing overhead worked so great for us thus far). **Buildpacks** are natively supported by **Cloud Build**, so we will use it as our build provider - by the way, this is exactly what happens under the hood when you deploy the **Cloud Functions**, as they currently run under the **Cloud Run** infrastructure. The command to deploy the backend service is as follows (make sure to adjust the region if you decided to go with another one and also make sure you moved to the app folder, because we're using the --source flag with current directory) - flags explanation is below the command in the hidden section.

<details>
<summary>gcloud command for deploying the Cloud Run backend</summary>

```bash
gcloud run deploy hello-backend \
  --source . \
  --region $REGION \
  --execution-environment gen2 \
  --service-account hello-backend-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --ingress internal \
  --network $NETWORK \
  --subnet $SUBNET \
  --vpc-egress all-traffic \
  --min-instances 1 \
  --set-env-vars INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:hello-game-db",DB_USER="hello-backend-sa@$PROJECT_ID.iam",DB_NAME="hello-game-submissions-db",ENVIRONMENT=production \
  --set-build-env-vars GOOGLE_ENTRYPOINT="gunicorn -b 0.0.0.0:8080 --log-level info --access-logfile - --error-logfile - src.main:app"
```

Now let's go through the arguments, as these are crucial at this moment:

`--source .` the source code; we need this since we're using **Buildpacks**; otherwise you would specify the container

`--execution-environment` gen2 is the default and more modern environment, gen1 is really only there for backwards compatibility

`--service-account` the service account that our app will run under

`--no-allow-unauthenticated` doesn't allow anonymous traffic to our service (meaning our frontend will need permissions to access it, which is exactly what we want)

`--ingress` restricts network access to the service; internal is the most restrictive option - this will have implications on our frontend setup later on; learn more [here](https://cloud.google.com/run/docs/securing/ingress)

`--network` and `--subnet` specify the VPC and subnet to route traffic through; as explained above this is required to enable the **Direct VPC egress** to work

`--vpc-egress` all-traffic routes all outbound traffic through the VPC, ensuring that all egress traffic goes through the VPC network, which is important for accessing resources like a private Cloud SQL instance; comes with a downside: it includes fetching Python packages during buildpacks runtime, cron jobs pinging APIs, etc, and traffic through the VPC is billed

`--min-instances` we will keep one instance running at all times in order to monitor our database probes

`--set-build-env-vars` sets build-time environment variables; we need to specify the entrypoint for our application since there is no Procfile present in the source code and there is main.py or app.py in the root of our source folder - the build will fail if we don't do this - if your application has simpler structure it's not needed, and we'll actually get away without it later when we deploy the hello-function. **Not** coincidentaly it is also the same command that would run when we call `make run`.

`--set-env-vars` sets environment variables for the application; **VERY IMPORTANT**: this is the implementation I've used (I mean the devs have used) and the variable names as well as how they operate are **specific to this application**:
- `INSTANCE_CONNECTION_NAME` - our application has the Cloud SQL Python Connector injected into it. The presence of this environment variable shifts the backend app into the GCP Cloud SQL IAM Auth mode and setups the connector. For the Cloud SQL connectors this needs to be in a format of `project:region:instance-name` (tip: you can run `gcloud sql instances describe hello-game-db --format="value(connectionName)"` to get the correct value)
- `DB_USER` - the database user corresponding to our service account - we do have to specify it, however it has to be the correct account pair, as otherwise the application would not be able to generate appropriate token to authenticate to the DB; also keep in mind the differences in the Service Account <-> Postgres DB User syntax
- `DB_NAME` - the database name we want to connect to. We are omitting it, as our by default our app will choose the DB I created before. If you created the DB under a different name you would have to specify it.

A small snippet from the code showing how only these three variables are used to create the DB connection, proving there are no passwords or other magic happening behind the curtains:
```python
        # --- Cloud SQL (production) with IAM Auth ---
        if Config.INSTANCE_CONNECTION_NAME:
            logger.info("Using Cloud SQL Python Connector (IAM Auth) for database connections.")
            connector = Connector()
            instance_name = Config.INSTANCE_CONNECTION_NAME

            def get_connection():
                logger.info("Establishing new connection using Cloud SQL Python Connector.")
                return connector.connect(
                    instance_connection_string=instance_name,
                    driver="pg8000",
                    user=Config.DB_USER,
                    db=Config.DB_NAME,
                    enable_iam_auth=True,     # IAM-based passwordless auth
                    ip_type=IPTypes.PRIVATE,  # PRIVATE or PUBLIC
                )
```
</details>

Now you might wonder: how the hell am I going to verify that the backend is working and able to connect (actually currently not connect because of the missing IAM roles) if I closed it off completely. While this is a great question and real concern for such a scenario and requirement - fear not. The application runs a DB Health Check probe every 30 seconds and logs the result. For ease of management of such highly restricted environments it would be my recommendation to have such a mechanism in place, but not only is this not a programming tutorial, I am also not a programmer - so **do not** take coding advice from me. (the way this probe is implemented is not really the best practice - the app has a /health health-check endpoint that would also log the result, however we can't directly access it - we would have to set up an uptime check in GCP that would hit it, but - spoiler alert - this will be scenario 2, and current implementation works out of the box)

Let's see what's going on then. This is really better done through the **Cloud Console**, so this time no gcloud command. Head over to **Cloud Run -> hello-backend -> Logs** and observe the logs. The connector throws some ugly stacktraces about not being able to connect to the database, so in the filter type `src.main` and you should see something like this:
```log
2025-12-19 09:53:43.291 CET 2025-12-19 08:53:43,290 - src.main - ERROR - DB Health Check: FAILED - Connection timeout to host https://sqladmin.googleapis.com/sql/v1beta4/projects/hello-game-app-477717/instances/hello-game-db/connectSettings
```
So what is this and what is going on, you were probably expecting a 403 or something of that sorts, since we didn't apply the IAM permissions. The Cloud Run is connected to the VPC, through the Direct VPC egress, the Cloud SQL instance is in the VPC, so this should be reachable. But here's the catch in our modern setup, if you remember correctly we've never passed any database information to our application other than the instance connection name. The Cloud SQL Python Connector uses the Cloud SQL Admin API to fetch the database instance metadata (IP address, SSL certs, etc) in order to establish the connection. But we've forced all of the egress traffic through the VPC, and have not enabled the access to Google APIs through that VPC. Meaning simply that our Cloud Run instance can't reach the Google APIs endpoints, as there is no routing set up. This will also come in handy later on when we deploy the frontend service, as it will also need to reach the backend service through the VPC. This [document](https://docs.cloud.google.com/run/docs/securing/private-networking#from-other-services) describes ways of forcing the Cloud Run services to access each other (and Google APIs) through the VPC instead of going through the public internet. We're going with option #1 which is:
> Make sure traffic to Cloud Run routes through the VPC network by using one of the following options:
> - Configure the source resource to route all traffic through the VPC network and enable Private Google Access on the subnet associated with Direct VPC egress [...].

To enable Private Google Access on our subnet run the following command:
```bash
gcloud compute networks subnets update $SUBNET \
  --region=$REGION \
  --enable-private-ip-google-access
```

Now a second round on the logs, different errors suggest that we're moving in the right direction, so do not get discouraged, filter the logs again by `src.main` and look for the line similar to this one:
```
2025-11-20 08:45:22,501 - src.main - ERROR - DB Health Check: FAILED - 403, message='boss::NOT_AUTHORIZED: Not authorized to access resource. Possibly missing permission cloudsql.instances.get on resource instances/hello-game-db.', url='https://sqladmin.googleapis.com/sql/v1beta4/projects/hello-game-app-477717/instances/hello-game-db/connectSettings'
```
which is expected because we deliberately skipped assigning the required IAM roles. Let's fix this and observe if this fixes the connection issues.

Suppress the inner voices trying to convince you to apply the cloudsql.admin role to the service account and just forget about it - repeat after me: *We are doing it the right way*. Remember that we've already set the required permission for the SA's database user, so this has been taken care of. What we're lacking at the moment is the ability for our application to connect and login to the database. As we're reducing our overhead, we're going to use the predefined roles for our IAM policies, these are pretty solid most of the times and should cover most of the use cases. Let's head over to the [available iam-roles](https://docs.cloud.google.com/sql/docs/postgres/iam-roles) and see if there's anything we can use. I encourage you to take a look yourself, below is the gcloud command that will grant the required permissions to the service account - did you choose the same role? Now before you apply these roles, look below into the commands, because as per usual, it comes with a quirk:
<details>
<summary>gcloud command for adding required IAM roles to the service account</summary>

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:hello-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.instanceUser" \
  --condition="expression=resource.name == 'projects/$PROJECT_ID/instances/hello-game-db' && resource.type == 'sqladmin.googleapis.com/Instance',title=is_hello-game-db_instance_user,description=Allows login to hello-game-db"
```
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:hello-backend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client" \
  --condition="expression=resource.name == 'projects/$PROJECT_ID/instances/hello-game-db' && resource.type == 'sqladmin.googleapis.com/Instance',title=is_hello-game-db_client,description=Allows connection to hello-game-db"
```
</details>

Now if you've missed the `roles/cloudsql.client` role, don't be too harsh on yourself as it's quite convoluted. Apparently the additional role that you get from it (`cloudsql.instances.connect`) is required for the IAM authentication to work, as it used to generate some certificates for the SSL connection, but do not quote me on this - you need both or it will not work (if you ask me I'd say if I add an instanceUser role to a user it should be able to connect as well, but well, GCP...). So to summarize, the required permissions are:

<details>
<summary>applied gcloud roles and why these</summary>

`cloudsql.instances.get` - this is used to fetch the metadata of the db to establish the connection (note that we didn't provide any connection details other than the database name - the connector uses this permission to get IP and such from the GCP API)

`cloudsql.instances.connect` - this is used and required to establish the safe connection using IAM auth

`cloudsql.instances.login` - this one is obvious - let's the account actually log in to the database instance
</details>

Now you're probably thinking: *What the hell are these conditions lines doing here?* At the moment the IAM bindings do not allow for fine grained Cloud SQL policies, but fear not, there is a workaround. Let's take a look at this [documentation](https://docs.cloud.google.com/sql/docs/mysql/iam-conditions#gcloud) that coincidentaly covers our scenario exactly. If you were too hasty and applied your's without the conditions you can just follow the example from the docs, pull your current bindings, apply the additional condition and push them:

<details>
<summary>gcloud commands for limiting IAM roles at the service account</summary>

```bash
gcloud projects get-iam-policy $PROJECT_ID --format=json > bindings.json
```
Add the required conditions to the file. If you want to be cheeky and make sure it actually works provide wrong DB Instance name and see what happens:

```json
{
  "bindings": [
    {
      "role": "roles/cloudsql.client",
      "members": [
        "serviceAccount:hello-backend-sa@$PROJECT_ID.iam.gserviceaccount.com"
      ],
      "condition": {
        "expression": "resource.name == 'projects/$PROJECT_ID/instances/hello-game-db' && resource.type == 'sqladmin.googleapis.com/Instance'",
        "title": "is_hello-game-db_client",
        "description": "Allows connection to hello-game-db"
      }
    }
  ],
  "etag": "BwWKmjvelug=",
  "version": 3
}
```
Save and push the updated policies:
```bash
gcloud projects set-iam-policy $PROJECT_ID bindings.json
```
</details>

> 💡 **Troubleshooting Tip:** These policies acted a little weird on me when creating this scenario. Sometimes they would not show up in the IAM section at all in the Cloud Console, but they would be present when running `gcloud projects get-iam-policy $PROJECT_ID`. Then when you tinker with the permissions from the Console a popup would sometimes appear showing these permissions and if you want to keep them. However do not fear, if you see your permissions attached from the gcloud command they **DO** work. How do I know this? I'm just that smart (*not really, I just wasted quite a bit of time trying to figure out what the heck is going on*).

After you implement the required policies go back to the Cloud Run Logs, the backend should be able to connect to the database now and you should see something like this in the logs:
```log
2025-12-06T22:06:39.900912Z 2025-12-06 22:06:39,900 - src.main - INFO - DB Health Check: SUCCESS - connection established.
```

🎉 **Congratulations!** You've successfully deployed the Cloud Run backend service and connected it to the private Cloud SQL database using IAM authentication!

> ### A note on Cloud Run networking setups and connection to Cloud SQL
> There are two ways of connecting Cloud Run to the VPC:
> 1. **Serverless VPC Access Connector** - the legacy way of connecting Cloud Run to the VPC. It provisions a set of VMs that act as a bridge between the managed service and your VPC. This comes with additional cost, as these VMs are billed even when idling. Also it complicates the networking setup, as you have to make sure that the connector is in the right region, has enough IPs reserved, etc.
> 2. **Direct VPC egress** - the modern way of connecting Cloud Run, already explained in detail above.  
>
> And to confuse us further there are two (actually three, but the first one is not really GCP specific) ways to connect your application to Cloud SQL:
> 1. **Direct Private IP connection** - the classic model: private IP, port 5432, username/password. Works fine, but requires manually managing credentials and making sure your service is inside the right VPC. The only caveat here is that we would have to connect the Cloud Run to the VPC so that it can resolve the DB's private IP.
> 2. **Cloud SQL Proxy sidecar (`--add-cloudsql-instances`)** - still very much functional but not recommended for most modern setups. Robust, but adds overhead. It runs a separate process alongside your application, consuming your container's CPU/RAM and adding a network hop. While it supports IAM, it typically requires your application code to manually fetch ephemeral tokens and pass them as passwords . The Python Connector handles this token rotation automatically behind the scenes, making the code cleaner.
> 3. **Cloud SQL Python Connector with IAM Auth** - the modern, recommended approach. Your application connects directly using short-lived IAM tokens generated via the connector, with no proxy and no secrets stored anywhere. This is what we used.
> 
> As a very wise young man from one of my all-time favourite shows once said: *“New is always better.”* - Barney Stinson (any fans in here?)
> So we went with the **Direct VPC egress** + **Cloud SQL Python Connector with IAM Auth** combo — the current best practice for connecting Cloud Run to Cloud SQL privately, securely, and without managing passwords.


### What you should have at this point:
✅ **1 Cloud Run Backend Service** - Your backend application running securely (with Direct VPC egress enabled)  
✅ **IAM Roles Assigned** - Proper permissions for database access

### 🔍 **Checkpoint Time!**
Let's run our verification script to make sure everything is properly configured. As always keep in mind that the script assumes you have named your resources exactly as specified in my workflow. Also we only verify if the roles are bound to the correct SA, we do not check if the conditions are applied correctly because I'm too lazy to implement that in a robust way:

```bash
# Move back to the scenario folder
cd ~/gcp-tutorials/scenarios/1/

# Make the script executable (if you haven't already)
chmod +x ./check-resources.sh

# Run the Task 3 verification
./check-resources.sh task-3
```
If you see **"All checks passed! (4/4)"** - you're on fire! 🔥


## Task 4 - Third layer part 2: finally something we can connect to - enter the frontend application
We're getting close, can you feel it? Closing the laptop and calling it a day... Let's deploy this frontend and get this over with. **BUT WAIT**, another trap we've set up for ourselves. Let's take a step back and think about our current setup. We have a backend service that we've cleverly closed off from all external traffic. And what is its address that it was given? Something like `https://hello-backend-908743237313.europe-central2.run.app`. Now this doesn't seem like an internal address to me, and so it won't to our frontend, which will then look for it on the public internet, it will find where it lies (because even though we don't allow public traffic to the service this address can be resolved to our backend globally, it just won't be allowed), go through the public web and **BOOM** - access denied since we only allow internal traffic. Luckily we are not the first ones to face this problem and there is a solution just for our case (actually there 3 solutions as per Google's docs, but we're going with the simplest one that fits our requirements, especially since we're 90% there already). And not only that, we've already set this up while deploying the backend service and facing the issue with DB connection. Remember the **Direct VPC egress**? We're going to use it here as well.

> ### 💡 Explanation time
> A little explanation on this: by enabling the **Private Google Access** on the subnet we're telling GCP that any requests to Google APIs (and Cloud Run uses Google Front Ends, which are internal Google services accessible via public DNS (the `app.run` domain)) made from within our subnet should be routed through Google's internal network instead of going through the public internet (the DNS is still public, but it will be routed internally). Next up we connect our frontend to the VPC using the  **Direct VPC egress** and set the `--vpc-egress` flag to `all-traffic`, effectively forcing all of the requests that the frontend makes to go through the VPC. This way we are forcing our frontend application to talk to the Google's services (which our backend is) through the internal network, which in exchange will satisfy the ingress rules of our backend service. Simple, isn't it?

Now as we did with our backend, let's navigate to the frontend source code folder and review what's in there:
```bash
cd ~/gcp-tutorials/hello-game-app/hello-frontend/
ls -la
ls src -la
```

Same story, no Dockerfile, nothing interesting really, so let's deploy it. Remember our requirements (force the traffic through the VPC, or our backend will not allow it), and the trick with GOOGLE_ENTRYPOINT so the **Buildpacks** know how to start our application (take a peek into the Makefile). This time we will use the `prod.env` file to pass the parameters (and clean up the deployment command a little). Take a look into the file, and verify that the `PUBSUB_TOPIC_ID` matches what you created. We also need to fill out two more mandatory variables: `GOOGLE_CLOUD_PROJECT` and `BACKEND_URL`. Here're the commands:

<details>
<summary>gcloud command for deploying the Cloud Run frontend</summary>

Inspect the `prod.env` file:
```bash
cat prod.env
```
Set up the `prod.env` file by adding the missing dynamic variables:

```bash
echo "GOOGLE_CLOUD_PROJECT='$PROJECT_ID'" >> prod.env

# Get the backend URL - sorry for this query, if there's a better way please let me know
# Run the command without the jq to see what we're dealing with here
BACKEND_URL=$(gcloud run services describe hello-backend --region $REGION --format json |
  jq -r '.metadata.annotations["run.googleapis.com/urls"] |
  fromjson |
  .[0]')

echo "BACKEND_URL='$BACKEND_URL'" >> prod.env
```

Verify that the `prod.env` contents look correct:
```bash
cat prod.env
```

Deploy the application:
```bash
gcloud run deploy hello-frontend \
  --source . \
  --region $REGION \
  --execution-environment gen2 \
  --service-account hello-frontend-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --ingress all \
  --network $NETWORK \
  --subnet $SUBNET \
  --vpc-egress all-traffic \
  --env-vars-file prod.env \
  --set-build-env-vars GOOGLE_ENTRYPOINT="gunicorn -b 0.0.0.0:8080 --worker-class gthread --threads 4 --timeout 60 --log-level info --access-logfile - --error-logfile - src.main:app"
```

Parameters explained:

`--source .` the source code; we need this since we're using **Buildpacks**; otherwise you would specify the container

`--execution-environment` as stated previously this is the default and current generation environment - can be omitted

`--service-account` the service account that our app will run under

`--allow-unauthenticated` allows anonymous traffic to our service (which is expected for a globally available frontend application)

`--ingress` allows traffic from all sources (internet + internal); since this is a public frontend we need to allow internet traffic

`--network` and `--subnet` specify the VPC and subnet to route traffic through; as explained in previous section this will enable the **Direct VPC egress** for our frontend

`--vpc-egress` as explained above, we force the outbound traffic to go through the VPC which in turn makes it internal when accessing Google APIs

`--env-vars-file` the file containing the environment variables for our application; we generated it just before the deployment command - an alternative to `--set-env-vars` used in backend deployment - again these are specific to the application:
- `GOOGLE_CLOUD_PROJECT` - the GCP project ID; used by the application to identify the Pub/Sub topic
- `PUBSUB_TOPIC_ID` - the Pub/Sub topic name; used by the application to publish messages to the topic
- `BACKEND_URL` - the URL of our backend service; used by the frontend to communicate with the backend

`--set-build-env-vars` as previously this is because we use **Buildpacks** and we need to instruct it on how to run our app


</details>

Try accessing the frontend URL and submitting a name. In the top right corner click on the **Statistics** button. Now as you've tested all of the functionality you can see that the backend communication is down (indicated by the mock data on the frontend) - and probably the name submission is failing as well. We have no permissions set just yet, so this is expected, let's head to the application logs, you should see something like this:

The Pub/Sub flow:
```log
2025-12-10 09:45:02.360 CET 2025-12-10 08:45:02,359 - src.main - INFO - Received name submission: test name
2025-12-10 09:45:02.360 CET 2025-12-10 08:45:02,360 - src.main - INFO - Publishing name to Pub/Sub: Test Name
2025-12-10 09:45:02.360 CET 2025-12-10 08:45:02,360 - src.main - INFO - Message publishing initiated in background thread
2025-12-10 09:45:02.594 CET 2025-12-10 08:45:02,594 - src.main - ERROR - Failed to publish message (Topic not found or access denied): 403 User not authorized to perform this action.
```

The backend statistics fetching flow:
```log
2025-12-10 09:44:53.692 CET 2025-12-10 08:44:53,691 - src.main - ERROR - Error fetching stats from backend: 403 Client Error: Forbidden for url: https://hello-backend-908743237313.europe-central2.run.app/stats
```

Let's fix these issues by assigning the required IAM roles to the service account. To be able to access the backend service we need to assign the `roles/run.invoker` role to the frontend service account. To be able to publish messages to Pub/Sub we need to assign the `roles/pubsub.publisher` role to the frontend service account. Remember about the principle of least privilege and scope the roles to the required resources only - luckily this time these permissions support scoping out of the box, so we don't have to resort to the conditions workaround that we did for the CloudSQL. Here are the commands:

<details>
<summary>gcloud commands for adding required IAM roles to the frontend service account</summary>

```bash
gcloud run services add-iam-policy-binding hello-backend \
  --region=$REGION \
  --member="serviceAccount:hello-frontend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

gcloud pubsub topics add-iam-policy-binding hello-game-submissions \
  --member="serviceAccount:hello-frontend-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

Note that for the Cloud Run role we have to specify the region, as Cloud Run services are regional resources. For the Pub/Sub role we don't do it, as Pub/Sub is a global resource.
</details>

Now go back to the frontend logs and try submitting a name again. You should see something like this:
```log
2025-12-10 17:13:20.933 CET 2025-12-10 16:13:20,933 - src.main - INFO - Received name submission: John Doe
2025-12-10 17:13:20.934 CET 2025-12-10 16:13:20,933 - src.main - INFO - Publishing name to Pub/Sub: John Doe
2025-12-10 17:13:21.037 CET 2025-12-10 16:13:21,036 - src.main - INFO - Published message ID: 16586736651794147
```

**Optional but encouraged:**

To verify that the name made it to the Pub/Sub topic we need to create a temporary subscription to the topic and pull the messages. Here's how to do it:
```bash
# Create the subscription
gcloud pubsub subscriptions create temp-subscription --topic=hello-game-submissions

# Pull messages from the subscription
gcloud pubsub subscriptions pull temp-subscription --auto-ack --limit=5

# Output should look like this:
DATA: John Doe
MESSAGE_ID: 16591036516519376
ORDERING_KEY: 
ATTRIBUTES: 
DELIVERY_ATTEMPT: 
ACK_STATUS: SUCCESS
```

Delete the temporary subscription as we will not need this for our application:
```bash
gcloud pubsub subscriptions delete temp-subscription
```

> ### 💡 Troubleshooting Tip:
> I can't really explain this, but for some reason the messages would sometimes not show up for me when pulling from the gcloud command. However it would work just fine when using the Cloud Console, and only after that the gcloud command would start showing the messages as well. So if you face this issue try checking the Cloud Console first.

Now go back to the frontend and check the statistics page again. You should see real data now fetched from the backend service, which funnily enough means an empty graph (as previously we were shown mock data). Go to the backend logs and you should see something like this:
```log
2025-12-10 17:42:17.033 CET GET200216 B18 mspython-requests/2.32.5 https://hello-backend-908743237313.europe-central2.run.app/stats
2025-12-10 17:42:17.060 CET 2025-12-10 16:42:17,060 - root - INFO - Retrieved stats from database successfully.
```

We're almost there, we're missing just the last piece of the puzzle - the Cloud Function that will process the Pub/Sub messages and write names to the database. However now is the time for the celebration!

🎉 **Congratulations!** You've successfully deployed the Cloud Run frontend service and connected it to the backend using internal networking!

### What you should have at this point:
✅ **Enabled Private Google Access** - Ensured internal routing for Google APIs inside of our VPC
✅ **1 Cloud Run Frontend Service** - Your frontend application running securely
✅ **IAM Roles Assigned** - Proper permissions for backend access and Pub/Sub publishing

### 🔍 **Checkpoint Time!**
Let's run the verification script to make sure everything is properly configured. As always keep in mind that the script assumes you have named your resources exactly as specified in my workflow:

```bash
# Make the script executable (if you haven't already)
chmod +x ./check-resources.sh

# Run the Task 4 verification
./check-resources.sh task-4
```
If you see **"All checks passed! (3/3)"** - you're almost there mate, thank you for putting up with me! 🌟

## Task 5 - Third layer part 3: the last piece of the puzzle - Cloud Function to process Pub/Sub messages
We're in the home stretch now, just one last component to deploy - the Cloud Function. Honestly, at this point it feels like we've faced every possible obstacle GCP can throw at us, so hopefully this will be smooth sailing. Let's navigate to the function source code folder and review what's in there:

```bash
cd ~/gcp-tutorials/hello-game-app/hello-function/
ls -la
```

Nothing fancy again. This will actually use **Buildpacks** behind the curtains to build the function's container. Let's deploy it. Remember our requirements (force the traffic through the VPC, or our database will not allow it). We can also set up the trigger right at the deployment time by specifying the Pub/Sub topic (you want to do this). And now GCP is back at it again. A little background - 2nd gen Cloud Functions actually run on Cloud Run infrastructure, and it is recommended that they are managed using the Cloud Run Admin API. Let's try a simple test (this little conundrum will not be seem through the Cloud Console, only when using gcloud CLI). Here's the deployment command:
<details>
<summary>gcloud command for deploying the Cloud Function</summary>

> ### ❗ Warning of what's to come ❗
> Below is a little bit of a rant on my part, some troubleshooting steps.  
> If you enjoy the way I'm going through this adventure then I recommend reading through it, otherwise skip to the command after the rant.  
> As stated above this is a gcloud CLI issue, it should not be present when deploying through the Cloud Console.  

<details>
<summary>Troubleshooting the mixup with Cloud Functions migration to Cloud Run</summary>

```bash
gcloud functions deploy hello-function \
  --region=$REGION \
  --gen2 \
  --runtime=python312 \
  --source . \
  --service-account=hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --entry-point=process_pubsub_message \
  --trigger-topic=hello-game-submissions \
  --network=$NETWORK \
  --subnet=$SUBNET \
  --vpc-egress=all-traffic \
  --set-env-vars INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:hello-game-db",DB_USER="hello-function-sa@$PROJECT_ID.iam",DB_NAME="hello-game-submissions-db",ENVIRONMENT=production
```

and 💥 **BOOM** 💥 - surprise:

```bash
ERROR: (gcloud.functions.deploy) unrecognized arguments:
  --network=hello-game-vpc (did you mean '--retry'?)
  --subnet=hello-game-subnet (did you mean '--quiet'?)
  --vpc-egress=all-traffic
  To search the help text of gcloud commands, run:
  gcloud help -- SEARCH_TERMS
```

Let's dig in briefly, and see what's going on in here. Just for the sake of it let's check the help for `gcloud functions deploy`:

```bash
gcloud functions deploy --help | grep -E "network|subnet|vpc-egress"
```

Nothing - let's double check the cloud run help:

```bash
gcloud run deploy --help | grep -E "network|subnet|vpc-egress"
```

looks solid. So now we have the Cloud Run function that supports the Direct VPC Egress (because it's gen 2, meaning it runs on Cloud Run and we already have a Cloud Run service with it deployed, so we know it does actually work), but we can't deploy it with the required flags? Let's take a step back and remember the recommendation - Cloud Run functions gen2 should be managed using the Cloud Run Admin API, let's continue our investigation there:

```bash
gcloud run deploy --help | grep -E "function"
```

and here's our answer:
```bash
At most one of these can be specified:

           [...]

           --function=FUNCTION
              Specifies that the deployed object is a function. If a value is
              provided, that value is used as the entrypoint.
```
So with this slightly long investigation we've not only found out that we should be deploying the function using `gcloud run deploy` instead of `gcloud functions deploy`, but we've also managed to stretch out this chapter that on the first glance seemed like a quick and easy one. Here's the command:
```bash
gcloud run deploy hello-function \
  --region=$REGION \
  --source . \
  --service-account=hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --function=process_pubsub_message \
  --trigger-topic=hello-game-submissions \
  --network=$NETWORK \
  --subnet=$SUBNET \
  --vpc-egress=all-traffic \
  --set-env-vars INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:hello-game-db",DB_USER="hello-function-sa@$PROJECT_ID.iam",DB_NAME="hello-game-submissions-db",ENVIRONMENT=production
```
and 💥 **BOOM** 💥 - another surprise:
```bash
ERROR: (gcloud.run.deploy) unrecognized arguments:
  --trigger-topic=hello-game-submissions
```

At this point we're banging our heads against the wall. This `--trigger-topic` flag is a godsend that sets up quite a bit of things for us during the Function deployment, but now we're stuck - we either deploy without the Direct VPC egress and the function will not work - or we deploy with it, but we can't use the one thing that GCP was handing to us on a silver platter. So, and now my brain is working at 200% capacity, let's get a little creative:
1. Deploy the function without the networking flags, but with the trigger topic using the `gcloud functions deploy` command - this will set up the function as a Cloud Run service and the EventArc trigger for us.
2. Update the function to add the networking flags using the `gcloud run services update` command - since we can manage functions set up as gen 2 using the Cloud Run Admin API this should work just fine.

</details>

> ### The reasoning for the workaround below (the two step deployment) is explained in detail in the **Troubleshooting...** dropdown section above.

```bash
# 1. Deploy the function (without networking flags first)
gcloud functions deploy hello-function \
  --region=$REGION \
  --gen2 \
  --runtime=python312 \
  --source . \
  --service-account=hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --entry-point=process_pubsub_message \
  --trigger-topic=hello-game-submissions \
  --set-env-vars INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:hello-game-db",DB_USER="hello-function-sa@$PROJECT_ID.iam",DB_NAME="hello-game-submissions-db",ENVIRONMENT=production
```
Now the function will be deployed, you will be able to see it in the Cloud Console, you can even go to it's **Networking** section and see that it's empty (compare to hello-backend for example). We know that this will not work because the function won't be able to connect to the database, we went through this with our backend setup. So let's update the function to add the required networking setup:
```bash
# 2. Update the function to add networking setup
gcloud run services update hello-function \
  --region=$REGION \
  --network=$NETWORK \
  --subnet=$SUBNET \
  --vpc-egress=all-traffic
```

This should spawn a new revision, you can again go to the Cloud Console, check the **Networking** section of the function and see that now it has the VPC and subnet assigned. That should do it. If it's stupid but it works, it ain't stupid. Right? Right?

> ### ❗ Important Note
> The 2 step deployment is obviously a workaround for a missing feature - it might be fixed or improved in the future, that was the state at the time of creating this tutorial and I have no idea if I will get back to it and update when Google patches this.


And finally - parameters explained:
`--runtime` the runtime environment for the function; in our case Python 3.12, this tells GCP which environment to set up for our function

`--gen2` deploys the function in the 2nd generation environment, which is crucial for our networking setup; gen1 does not support Direct VPC egress

`--service-account` the service account that our function will run under

`--no-allow-unauthenticated` doesn't allow anonymous traffic to our function (which we want since it will be triggered by Pub/Sub only); this is actually the default behaviour for Cloud Functions, so this flag is optional

`--entry-point` the name of the function inside of our source code that will be executed when the function is triggered

`--trigger-topic` the Pub/Sub topic that will trigger the function; this will set up an EventArc trigger behind the scenes for us and not only that - this comes with all the required permissions out of the box (well, almost but we'll get to it soon) - finally Google is giving us something

`--network` and `--subnet` (applied in step 2) specify the VPC and subnet to route traffic through; as explained in previous section this will enable the **Direct VPC egress** for our function

`--vpc-egress` (applied in step 2) as explained above, we force the outbound traffic to go through the VPC which in turn makes it internal when accessing Google APIs

`--set-env-vars` sets environment variables for the application; same as with the backend and frontend these are specific to this application. Again, note that **we don't provide any passwords or secrets**:
- `INSTANCE_CONNECTION_NAME` - our function has the Cloud SQL Python Connector injected into it. The setup is the exact same as for the backend - for the Cloud SQL connectors this needs to be in a format of `project:region:instance-name` (tip: you can run `gcloud sql instances describe hello-game-db --format="value(connectionName)"` to get the correct value)
- `DB_USER` - the database user corresponding to our service account - we do have to specify it, however it has to be the correct account pair, as otherwise the application would not be able to generate appropriate token to authenticate to the DB; also keep in mind the differences in the Service Account <-> Postgres DB User syntax
- `DB_NAME` - the database name we want to connect to
</details>

Before we apply the required IAM roles let's take a look what's going on in the function logs. You should see something like this (if you have messages waiting in the Pub/Sub queue, if not - post something through the frontend first):
```log
2025-12-10 18:46:11.313 CET POST 403 0B 0ms APIs-Google; (+https://developers.google.com/webmasters/APIs-Google.html) https://hello-function-lbnmovjjsq-lm.a.run.app/?__GCP_CloudEventsMode=CUSTOM_PUBSUB_projects%2Fhello-game-app-477717%2Ftopics%2Fhello-game-submissions 
```

#### 🔑 Why we get a 403
Earlier in the explanations I mentioned that the EventArc trigger that gets created when we specify the `--trigger-topic` flag automatically assigns the required permissions. However, let's break down what is happening step by step:
1. The EventArc watches the Pub/Sub topic for new messages
2. A new message arrives and triggers the EventArc
3. The EventArc sends a POST request to the function that is supposed to trigger it
Up to this point we're all good, all required permissions are in place out-of-the-box. But Cloud Run blocks the request because EventArc is invoking the function as a service account, and that identity doesn’t yet have permission to call the function. This is as far as Google has covered us. We need the `roles/run.invoker` on the triggering identity. But what is triggering the function? Let's inspect the EventArc trigger:

```bash
gcloud eventarc triggers describe $(gcloud eventarc triggers list --format="value(name)") --location $REGION
```
Expected output snippet (some data omitted for clarity)
```yaml:
destination:
  cloudFunction: projects/hello-game-app-477717/locations/europe-central2/functions/hello-function
eventFilters:
- attribute: type
  value: google.cloud.pubsub.topic.v1.messagePublished
name: projects/hello-game-app-477717/locations/europe-central2/triggers/hello-function-874439
serviceAccount: hello-function-sa@hello-game-app-477717.iam.gserviceaccount.com   <---
transport:
  pubsub:
    subscription: projects/hello-game-app-477717/subscriptions/eventarc-europe-central2-hello-function-874439-sub-020
    topic: projects/hello-game-app-477717/topics/hello-game-submissions
```
Note the serviceAccount field: `serviceAccount: hello-function-sa@hello-game-app-477717.iam.gserviceaccount.com` - this is the identity that the trigger uses to invoke the function. Interestingly enough this is the same account that we specified for the function itself. Now this could be altered through the `--trigger-service-account` flag when deploying the function. However using the same identity for both the runtime and the trigger is the default behavior and simplifies our setup without introducing additional service accounts.

<details>
<summary>gcloud command for adding required IAM role to the function service account</summary>

```bash
# Grant the invoker role to the function service account so the trigger can invoke the function
gcloud run services add-iam-policy-binding hello-function \
  --member="serviceAccount:hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=$REGION
```

And the roles to connect to the database, just like to backend service:
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.instanceUser" \
  --condition="expression=resource.name == 'projects/$PROJECT_ID/instances/hello-game-db' && resource.type == 'sqladmin.googleapis.com/Instance',title=is_hello-game-db_instance_user,description=Allows login to hello-game-db"
```
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:hello-function-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client" \
  --condition="expression=resource.name == 'projects/$PROJECT_ID/instances/hello-game-db' && resource.type == 'sqladmin.googleapis.com/Instance',title=is_hello-game-db_client,description=Allows connection to hello-game-db"
```
</details>

Now with everything in place, try submitting a name through the frontend and then check the **Statistics** page - the name should show up on the graph and stats. I've also prepared a script that will push random names to the Pub/Sub topic so you can see the data flowing in. By default it will push 50 names in 2 second intervals, if you want you can adjust these inside of the script - it's not rocket science. Here's how to run it:
```bash
cd ~/gcp-tutorials/scenarios/1/

# Make the script executable
chmod +x ./names-injector.py

# Run the script
FRONTEND_URL=$(gcloud run services describe hello-frontend --region $REGION --format json | jq -r '.metadata.annotations["run.googleapis.com/urls"] | fromjson | .[0]')

FRONTEND_URL=$FRONTEND_URL python3 ./names-injector.py
```

And voilà, you should see the names appearing on the statistics page in real-time! The application is now fully functional, with the frontend, backend, Pub/Sub, Cloud Function, and Cloud SQL all working together seamlessly and securely. 

🎉 **Congratulations!** You've successfully deployed the Cloud Function and completed the entire architecture! Now you can enjoy playing with the amazing application that we've just deployed. Or, you know, scrap the project so you don't incur any additional costs.

Before you go ahead and delete all the resources, here's what you should have at this point:
✅ **1 Cloud Function** - Your function processing Pub/Sub messages and writing to the database
✅ **IAM Roles Assigned** - Proper permissions for function invocation and database access

### 🔍 **Final Checkpoint Time!**
Let's run the verification script to make sure everything is properly configured. As always keep in mind that the script assumes you have named your resources exactly as specified in my workflow:

```bash
# Make the script executable (if you haven't already)
chmod +x ./check-resources.sh

# Run the Task 5 verification
./check-resources.sh task-5

# Alternatively, run all tasks verification
./check-resources.sh all
```


On the final note - it's impressive how one, seemingly simple requirement - "make all the backend traffic internal only" - can lead to such a complex setup with multiple components. This exercise highlights the importance of understanding GCP's networking and security features, as well as the need for careful planning when designing cloud architectures. Kudos to you for making it through this challenging scenario!


# Final Note 🔒
The security and overall best practices world is vast and ever-evolving. In this scenario we've **focused** on a particular set of requirements and implemented a solution that meets them, while skipping over a couple of red flags - the reason being, not to clutter the scenario with too many concepts at once (i.e. our initial DB migration strategy, which I've also used as an entrypoint for a, sadly, relatable joke). In a real-world production setup you would obviously want to address these as well - which to make myself look better and highlight that I know this -  I am acknowledging in this final note.