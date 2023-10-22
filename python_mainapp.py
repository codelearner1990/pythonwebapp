from flask import Flask, render_template, request
import subprocess
import json
import os


app = Flask(__name, static_folder='static')

# Define a list of domain and environment names
domain_names = ['codetest-abc-token-requestors', 'codetest-puppi-idv', 'codetest-puppi-transconf', 'codetest-abc-apple', 'codetest-abc-boarding', 'codetest-abc-cryptograms', 'codetest-abc-issuer', 'codetest-abc-par', 'codetest-abc-perso', 'codetest-abc-provisioning', 'codetest-abc-token', 'codetest-abc-trapple', 'codetest-abc-trdc', 'codetest-abc-zws']
regions = ["prd1-us-east-1", "prd1-us-west-2", "dev1-us-east-1", "dev1-us-west-2", "prd2-us-east-1", "prd2-us-west-2", "dev2-us-east-1", "dev2-us-west-2"]

# This is a list of fields to exclude from the output
exclude_fields = ['subnetgroup', 'vpcSecurityGroupIds', 'tags', 'ownerEmail', 'maintenanceWindow', 'backupWindow', 'subnetGroup', 'vpcSecurityGroupIds', 'configureDBLibs']

multiAZ_suffixCheck = ['prod', 'stage', 'perf']
multiAZ_prodCheck = ['prod', 'stage']

pricing_data = []

def read_pricing_data():
    global pricing_data

    with open("pricing_data", "r") as pricing_file:
        pricing_data = json.load(pricing_data)

read_pricing_data()

def calculate_cost(node_type, storage_type, region, multiAZ=False, allocatedstorage=0):
    cost = "NA"
    stroage_costs = {}
    for item in pricing_data:
        if item.get("nodeType") == node_type and item.get("region") == region:
            cost_data = item.get("cost", {})
            if multiAZ and "multiAZ" in cost_data:
                cost = 730 * float(cost_data["multiAZ"]) + allocatedstorage * (float(stroage_costs.get(storage_type, 0)))

            elif "singleAZ" in cost_data:
                cost = 730 * float(cost_data["singleAZ"]) + allocatedstorage * (float(stroage_costs.get(storage_type, 0)))

    print(f"after: {cost}")

    return cost


def login_to_openshift(region, username, password):
    # Securely capture the *****
    # ***** = getpass.getpass(f"Enter your ***** for {*****} to login {region}: ")

    # Define the cluster URLs for different regions
    cluster_urls = {
        "prd-us-east-1": "https://api.aws-useast1-apps-prod-1.ocpprd.us-east-1.ac.xx:6443",
        "prd-us-west-2": "https://api.aws-uswest2-apps-prod-1.ocpprd.us-west-2.ac.xx:6443",
        "dev-us-east-1": "https://api.aws-useast1-apps-dev-2.ocpdev.us-east-1.ac.xx:6443",
        "dev-us-west-2": "https://api.aws-uswest2-apps-dev-1.ocpdev.us-west-2.ac.xx:6443"
    }

    # Set the cluster URL based on the region
    cluster_url = cluster_urls.get(region)

    # Log in to OpenShift using the provided credentials
    login_command = f'oc login {cluster_url} --username={username} --password={password}'
    subprocess.run(login_command, shell=True)

def capture_openshift_data(region):
    # Run the 'oc get postgresql' command
    command = f'oc get postgresql --all-namespaces -o json'
    result = subprocess.check_output(command, shell=True)

    # Parse the JSON output
    data = json.loads(result)

    # Filter data for specified namespaces
    filtered_data = []
    for item in data['items']:
        namespace = item.get("metadata", {}).get("namespace")
        if not namespace:
            continue
        for domain_name in domain_names:
            if namespace.startswith(f"{domain_name}-"):
                node_type = item.get("spec", {}). get("nodeType", "UNKNOWN")
                storage_type = item.get("spec", {}). get("storageType", "UNKNOWN")
                region = item.get("spec", {}). get("awsRegion", "UNKNOWN")
                multiAZ = item.get("spec", {}). get("multiAZ", False)
                allocatedstorage = item.get("spec", {}). get("allocatedStorageSize", "UNKNOWN")
                cost = calculate_cost(node_type, storage_type, region, multiAZ, allocatedstorage)
                item["COST"] = round(cost,2)
                # Filter item based on exclude_fields
                filtered_item = {key: value for key, value in item.items() if key not in exclude_fields}
                filtered_data.append(filtered_item)

    return filtered_data


def apply_conditions(item):
    namespace_suffix = item['metadata']['namespace'].lower()
    if (
        item.get("spec", {}).get("multiAZ", False) and not namespace_suffix.endswith(tuple(multiAZ_suffixCheck))
    ):
        return "condition-1"

    elif (
           item.get("spec", {}).get("multiAZ", False) and not namespace_suffix.endswith(tuple(multiAZ_prodCheck))

    ):
        return "condition-2"
    return ""


@app.route('/generate-postgresql-html', methods=['GET', 'POST'])
def execute_and_generate_html():
    if request.method == 'POST':
        data = []
        username = request.form['username']
        password = request.form['password']

        for region in regions:
            login_to_openshift(region, username, password)
            region_data = capture_openshift_data(region)
            data.extend(region_data)

        all_fields = set()
        for item in data:
            all_fields.update(item.get('spec', {}).keys())

        for item in data:
            item['highlight'] = apply_conditions(item)

        return render_template('postgresql_template.html', data=data, all_fields=all_fields, exclude_fields=exclude_fields)

    # Display a login form with the ***** pre-filled
    username = os.environ.get("USER", "")  # Get the ***** from the environment variable
    return render_template('login.html', username=username)

if __name__ == '__main__':
    app.run(debug=True)
