# cryptotronbot-portfolio
contact ifocus1776 to be added to repo
Cryptocurrency Portfolio Tracker AI agent

Use a Virtual Environment
Here’s how to set up a virtual environment and install your packages.

1. Create the Virtual Environment

Navigate to your project's root directory (where your requirements.txt file is) in the Terminal and run the following command. It's common to name the virtual environment folder venv.

Bash
python3 -m venv venv

You will see a new folder named venv in your project directory.

1. Activate the Virtual Environment
Before you can install packages into the virtual environment, you need to activate it.

Bash
source venv/bin/activate

Once activated, your terminal prompt will usually change to show the name of the virtual environment, like (venv).

1. Install Your Packages

Now that you are inside the virtual environment, you can safely install your project's dependencies using pip.

Bash
pip install -r requirements.txt

This command will now install the packages listed in your requirements.txt file into the venv folder, not into the system-wide Python.

Moving Forward:

Deactivating: When you are done working on your project, you can deactivate the environment by simply typing deactivate in the terminal.
Reactivating: The next time you work on your project, remember to navigate to the project directory and reactivate the virtual environment with source venv/bin/activate.
Using virtual environments is a core practice in modern Python development that helps manage dependencies and avoid the exact error you encountered.

To run the frontend (Sinatra):
1. bundle install
1. ruby app.rb
1. Open your browser to http://localhost:4567 (default Sinatra port).

To run the backend (conceptual):
1. pip install -r requirements.txt
1. flask db init (first time)
1. flask db migrate -m "Initial migration"
1. flask db upgrade
1. python app.py


