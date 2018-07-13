"""Takes coreos provided AMIs file coreos_production_ami_all.json and converts it to the generic base_images.json format
"""

import os
import json

for root, dirs, files in os.walk(os.getcwd()):
    if 'coreos_production_ami_all.json' in files:
        with open(os.path.join(root, 'coreos_production_ami_all.json'), 'r') as f1:
            with open(os.path.join(root, 'base_images.json'), 'w') as f2:
                result = {}
                content = json.load(f1)
                for entry in content['amis']:
                    result[entry['name']] = entry['hvm']
                f2.write(json.dumps(result))
