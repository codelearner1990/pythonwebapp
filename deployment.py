 def capture_deployment_data(region):
    # Example command; adjust if needed
    command = f'oc get deployments --all-namespaces -o json'
    result = subprocess.check_output(command, shell=True)

    # Parse the JSON output
    deployments = json.loads(result)

    deployment_details = []
    for item in deployments['items']:
        namespace = item['metadata']['namespace']
        
        spec = item['spec']
        template_labels = spec['template']['metadata'].get('labels', {})
        componentName = template_labels.get('componentName', None)
        containers = spec['template']['spec']['containers']

        main_container = next((container for container in containers if container['name'] == componentName), None)

        probes = {}
        resources = {}
        if main_container:
            probes = {
                'liveness_probe': main_container.get('livenessProbe', 'None'),
                'readiness_probe': main_container.get('readinessProbe', 'None'),
                'startup_probe': main_container.get('startupProbe', 'None'),
            }
            resources = main_container.get('resources', 'None')

        detail = {
            'namespace': namespace,
            'name': item['metadata']['name'],
            'replicas': spec.get('replicas', 'Unknown'),
            'strategy_type': spec.get('strategy', {}).get('type', 'Unknown'),
            'assignment_group': template_labels.get('assignmentGroup', 'Unknown'),
            'support_assignment_group': template_labels.get('supportAssignmentGroup', 'Unknown'),
            'container_image': main_container['image'] if main_container else 'Unknown',
            'probes': probes,
            'resources': resources,
        }

        deployment_details.append(detail)

    return deployment_details




@app.route('/generate-deployments-html', methods=['GET', 'POST'])
def generate_deployments_html():
    if request.method == 'POST':
        data = []
        username = request.form['username']
        password = request.form['password']

        for region in regions:  # Ensure 'regions' is defined globally or accessible here
            try:
                # Assuming login_to_openshift() logs in and sets up context for subsequent commands
                login_to_openshift(region, username, password)
                region_data = capture_deployment_data(region, username, password)
                data.extend(region_data)
            except Exception as e:
                print(f"Error processing data for region {region}: {str(e)}")
                continue

        # No need for 'all_fields' calculation here unless you have a dynamic set of fields to display
        return render_template('deployments_template.html', deployments=data)

    # Display the login form if the request is not POST
    # Assuming a similar login.html template exists that posts 'username' and 'password'
    return render_template('login.html', username=os.environ.get("USER", ""))



<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kubernetes Deployments</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
</head>
<body>
<div class="container mt-4">
    <h1>Kubernetes Deployments</h1>
    {% for deployment in deployments %}
        <div class="card mb-3">
            <div class="card-header">{{ deployment['namespace'] }} - {{ deployment['name'] }}</div>
            <div class="card-body">
                <p>Replicas: {{ deployment['replicas'] }}</p>
                <p>Strategy: {{ deployment['strategy_type'] }}</p>
                <p>Main Container Image: {{ deployment['container_image'] }}</p>
                <!-- Add more deployment details as needed -->
            </div>
        </div>
    {% endfor %}
</div>
</body>
</html>


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kubernetes Deployments</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    <style>
        .container { margin-top: 20px; }
        .deployment-card { margin-bottom: 20px; }
    </style>
</head>
<body>
<div class="container">
    <h1>Kubernetes Deployments</h1>
    <div class="row">
        {% for deployment in deployments %}
            <div class="col-md-4">
                <div class="card deployment-card">
                    <div class="card-body">
                        <h5 class="card-title">{{ deployment.name }}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">{{ deployment.namespace }}</h6>
                        <p class="card-text">
                            Replicas: {{ deployment.replicas }}<br>
                            Strategy: {{ deployment.strategy_type }}<br>
                            Assignment Group: {{ deployment.assignment_group }}<br>
                            Support Assignment Group: {{ deployment.support_assignment_group }}<br>
                            Main Container Image: {{ deployment.container_image }}<br>
                            Resources: {{ deployment.resources|tojson }}<br>
                            Probes: 
                            <ul>
                                <li>Liveness: {{ deployment.probes.liveness_probe|tojson }}</li>
                                <li>Readiness: {{ deployment.probes.readiness_probe|tojson }}</li>
                                <li>Startup: {{ deployment.probes.startup_probe|tojson }}</li>
                            </ul>
                        </p>
                    </div>
                </div>
            </div>
        {% endfor %}
    </div>
</div>
<script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
</body>
</html>

