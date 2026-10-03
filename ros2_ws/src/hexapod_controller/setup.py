from setuptools import setup

package_name = "hexapod_controller"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/controllers.yaml"]),
        ("share/" + package_name + "/launch", ["launch/controller.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "tripod_gait_controller = hexapod_controller.gait_controller:main",
        ],
    },
)
