import paramiko
import pandas as pd
import os
import traceback
import time
import socket

# Start timing
start_time = time.time()

# Function to execute commands on MikroTik router via SSH
def execute_command(ssh_client, command):
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            print(f"\nError: {error}\n")
        return output
    except Exception as e:
        print(f"\nError executing command: {command}\n")
        print(e)
        traceback.print_exc()
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

# Function to configure the MikroTik router
def configure_router(link_name, wan, bridge_ip, dhcp_network, dhcp_pool, nvr_ip, tunnel_ip, username, password):
    try:
        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(wan, username=username, password=password, banner_timeout=40)

        print(f"\nConnected to {wan} via SSH session:\n")
        print("Configuring...")

        # Step 1: Configure IP address on bridge1 interface
        lan_address = f"{bridge_ip}/24"  # Bridge IP address
        execute_command(ssh_client, f'/ip address set [/ip address find interface="Bridge1"] address={lan_address}')
        print(f"\nUpdated IP address {lan_address} on Bridge1.")
        time.sleep(1)

        # Step 2: Update DHCP server network and gateway
        execute_command(ssh_client, f"/ip dhcp-server network set 0 address={dhcp_network} gateway={bridge_ip}")
        print(f"Updated DHCP network {dhcp_network} with gateway {bridge_ip}.")
        time.sleep(1)

        # Step 3: Update IP Pool range to the specified pool range
        execute_command(ssh_client, f"/ip pool set 0 ranges={dhcp_pool}")
        print(f"Updated DHCP pool range to {dhcp_pool}.")
        time.sleep(1)

        # Step 4: Configure IP tunnel with the remote address
        remote_ip = '43.252.198.121'  # Remote IP address for the tunnel
        execute_command(ssh_client, f"/interface ipip add name=To-DC remote-address={remote_ip}")
        print(f"Configured IP tunnel with remote address {remote_ip}.")
        time.sleep(1)

        # Step 5: Update NVR IP in NAT Rules
        execute_command(ssh_client, f"ip firewall nat set [/ip firewall nat find to-addresses=192.168.1.5] to-addresses={nvr_ip}")
        print(f"Configured NAT Rule {nvr_ip}.")
        time.sleep(1)

        # Step 6: Update Masqurade
        execute_command(ssh_client, f'ip firewall nat set [/ip firewall nat find src-address="192.168.1.0/24"] src-address={dhcp_network}')
        print(f"Configured Masqurade Rule {dhcp_network}.")
        time.sleep(1)

        # # Step 7: Add Static Route
        # execute_command(ssh_client, f'ip route add dst-address={dhcp_network} gateway="To-DC"')
        # print(f"Configured Static Route.")
        # time.sleep(1)

        # Step 8: Add Backup Mail ID
        script1 = '/system backup save name=email'
        script2 = ':delay 10s'
        script3 = f'/export file={link_name}.rsc'
        script4 = ':delay 10s'
        script5 = f'/tool e-mail send to=support.ahmedabad@gtpl.net cc=amit.patel@gtpl.net subject=([/system identity get name].\\" Backup\\") file={link_name}.rsc'
        script6 = ':delay 40s'
        script7 = ':log info \\"Backup e-mail sent.\\"'
        execute_command(ssh_client, f'/system scheduler add interval=1w20m name="E-Mail Backup" on-event=BackupMail policy=ftp,reboot,read,write,policy,test,password,sniff,sensitive,romon start-date=sep/30/2020 start-time=11:52:18')
        execute_command(ssh_client, f'/system script add dont-require-permissions=no name=BackupMail owner=Girish policy=ftp,reboot,read,write,policy,test,password,sniff,sensitive,romon source="{script1}\\r\\ \\n{script2}\\r\\ \\n{script3}\\r\\ \\n{script4}\\r\\ \\n{script5}\\r\\ \\n{script6}\\r\\ \\n{script7}"')
        execute_command(ssh_client, f'/tool e-mail set server=mail.gtpl.net from=backup.epcrouter@gtpl.net password=BAckUP#EPC#Router#062024 port=587 tls=yes user=backup.epcrouter')
        execute_command(ssh_client, f'/ip dns set servers=8.8.8.8,8.8.4.4,2001:4860:4860::8888,2001:4860:4860::8844')
        execute_command(ssh_client, f'/system clock manual set time-zone=+05:30')
        execute_command(ssh_client, f'/system ntp client set enabled=yes servers=27.116.54.34')
        print("Script Added Successfully.")
        time.sleep(1)

        # Step 9: Configure Tunnel IP:
        execute_command(ssh_client, f'/ip address add address="{tunnel_ip}" interface=To-DC')
        print(f'Tunnel IP {tunnel_ip} configured on interface To-DC.')
        time.sleep(1)

        # Step 10: Configure Identity:
        execute_command(ssh_client, f'/system identity set name="{link_name}"')
        print(f'Identity {link_name} set for Router {wan}.\n')
        time.sleep(1)

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        # Print the final configurations applied on the router
        print(f"\nConfiguration summary for router {wan}:\n")

        # Fetch and print the IP address configured on bridge1
        lan_address_output = execute_command(ssh_client, f'/ip address print where address="{lan_address}"')
        print(f" - IP address on Bridge1:\n{lan_address_output}\n")

        # Fetch and print the DHCP network settings
        dhcp_network_output = execute_command(ssh_client, f"/ip dhcp-server network print")
        print(f" - DHCP Network:\n{dhcp_network_output}\n")

        # Fetch and print the IP Pool range
        dhcp_pool_output = execute_command(ssh_client, f"/ip pool print")
        print(f" - DHCP Pool:\n{dhcp_pool_output}\n")

        # Fetch and print the IP tunnel settings
        tunnel_output = execute_command(ssh_client, "/interface ipip print")
        print(f" - IP Tunnel:\n{tunnel_output}\n")

        # Print NAT Rules
        nat_rules = execute_command(ssh_client, f"ip firewall nat print where to-addresses={nvr_ip}")
        print(f" - DST-NAT:\n{nat_rules}\n")

        # Print Masqurade Rule
        src_rules = execute_command(ssh_client, f'ip firewall nat print where src-address="{dhcp_network}"')
        print(f" - SRC-NAT:\n{src_rules}\n")

        # # Print Static Route:
        # static_route = execute_command(f'ip route print where gateway="To-DC"')
        # print(f" - Static-Route: {static_route}\n")

        # print script content:
        schedular = execute_command(ssh_client, '/system scheduler print')
        print(f" - Schedular: \n{schedular}\n")
        script_p = execute_command(ssh_client, '/system script print')
        print(f" - Script: \n{script_p}\n")
        e_mail = execute_command(ssh_client, '/tool e-mail print')
        print(f" - E-Mail: \n{e_mail}\n")
        dns = execute_command(ssh_client, '/ip dns print')
        print(f" - DNS: \n{dns}\n")
        clock = execute_command(ssh_client, '/system clock print')
        print(f" - Clock: \n{clock}\n")
        ntp = execute_command(ssh_client, '/system ntp client print')
        print(f" - NTP-Client: \n{ntp}\n")

        # Print Tunnel IP Config:
        tun_ip = execute_command(ssh_client, f'/ip address print where address="{tunnel_ip}"')
        print(f' - Tunnel IP: \n{tun_ip}\n')

        # Print Router Identity:
        identity = execute_command(ssh_client, f'/system identity print')
        print(f' - Router Name is: \n{identity}\n')

        # Close the SSH connection
        ssh_client.close()
        print("#################################################################################################")
        print("#################################################################################################")

    except Exception as e:
        print(f"\nFailed to configure {wan}: {e}\n")
        traceback.print_exc()
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

# Function to check if the router is reachable via ping
def ping_router(ip):
    try:
        command = f'ping -n 2 {ip}'
        response = os.popen(command).read()  # Execute the ping command and capture the output

        # Check if the response contains specific phrases:
        if f"Reply from {ip}:" in response:
            return True
        
        elif "Destination host unreachable" in response or "Request timed out" in response:
            print(response)
            return False

        else:
            print("\nUnexpected ping response\n")
            print(response)
            return False

    except Exception as e:
        print(f"\nPing failed for {ip}: {e}\n")
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
        return False

# Function to read router details from Excel file
def read_router_details(excel_file):
    df = pd.read_excel(excel_file)
    return df[['Link Name', 'WAN', 'Bridge IP', 'DHCP Network', 'Pool', 'NVR IP', 'Tunnel IP']]

# Main function to configure all routers
def configure_all_routers(excel_file, username, password):
    success_count = 0
    failure_count = 0
    unreachable_count = 0
    try:
        # Read router details from Excel
        router_details = read_router_details(excel_file)

        # Iterate through the routers and apply configurations
        for index, row in router_details.iterrows():
            link_name = row['Link Name']
            wan = row['WAN']
            bridge_ip = row['Bridge IP']
            dhcp_network = row['DHCP Network']
            dhcp_pool = row['Pool']
            nvr_ip = row['NVR IP']
            tunnel_ip = row['Tunnel IP']

            # Check connectivity before connecting through SSH
            print(f"\nChecking connectivity to {wan}...")
            if ping_router(wan):
                print(f"\n{wan} is reachable. Connecting via SSH...\n")
                
                failure_flag = False  # Reset failure flag for each router

                try:
                    # Attempt to configure the router
                    configure_router(link_name, wan, bridge_ip, dhcp_network, dhcp_pool, nvr_ip, tunnel_ip, username, password)
                    # If configuration is successful, increment success counter
                    success_count += 1
                
                except Exception as e:
                    # If configuration fails due to an exception, increment failure counter
                    if not failure_flag:
                        print(f"\nError configuring router {wan}: {e}")
                        failure_count += 1
                        failure_flag = True  # Set flag to avoid double counting

            else:
                print(f"\n{wan} is not reachable. Skipping to the next router.\n")
                print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
                unreachable_count += 1  # Count this as an unreachable router

            time.sleep(2)  # Optional: Add a delay between configurations to prevent overload


    except Exception as e:
        print(f"\nError in processing the routers: {e}\n")
        traceback.print_exc()
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
        failure_count += 1

    # Print final configuration status
    print(f"\nConfiguration Summary:")
    print(f"\nTotal routers configured successfully: {success_count}\n")
    print(f"\nTotal routers failed to configure: {failure_count}\n")
    print(f"\nTotal unreachable routers: {unreachable_count}\n")

if __name__ == "__main__":
    # Define login credentials and Excel file path
    username = 'admin'  # Replace with your admin username
    password = 'admin'  # Replace with your admin password
    excel_file = 'GSCSC_Config.xlsx'  # Replace with your Excel file path
    
    # Configure all routers based on the Excel file
    configure_all_routers(excel_file, username, password)

# End timing
end_time = time.time()
execution_time = end_time - start_time
print(f"\nTotal execution time: {execution_time:.2f} seconds\n")


