import os

def ping(ip_address):
    # Run the ping command and capture the output
    command = f'ping -n 2 {ip_address}'

    os.system(command)
    
    response = os.popen(command).read()  # Execute the ping command and capture the output

    # Check if the response contains specific phrases
    if "Destination host unreachable" in response or "Request timed out" in response:
        print("\nNot connected\n")
    elif f"Reply from {ip_address}:" in response:
        print("\nConnected\n")
    else:
        print("\nUnexpected ping response\n")

# Test with an example IP address (replace with any IP you want to test)
ping("10.130.192.1")  # Example IP (Google DNS)
