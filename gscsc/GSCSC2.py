import paramiko
import pandas as pd
import os
import traceback
import time
import socket

# Start timing
start_time = time.time()

# Open output file to write logs
output_file = open("output.txt", "w")

# Function to execute commands on MikroTik router via SSH
def execute_command(ssh_client, command):
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            print(f"\nError: {error}\n")
            output_file.write(f"\nError: {error}\n")
        return output
    except Exception as e:
        print(f"\nError executing command: {command}\n")
        output_file.write(f"\nError executing command: {command}\n")
        print(e)
        traceback.print_exc()
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
        output_file.write("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

# Function to configure the MikroTik router
def configure_router(link_name, wan, bridge_ip, dhcp_network, dhcp_pool, nvr_ip, tunnel_ip, username, password):
    try:
        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(wan, username=username, password=password, banner_timeout=40)

        print(f"\nConnected to {wan} via SSH session:\n")
        output_file.write(f"\nConnected to {wan} via SSH session:\n")
        print("Configuring...")
        output_file.write("Configuring...\n")

        # Step 1: Configure IP address on bridge1 interface
        lan_address = f"{bridge_ip}/24"  # Bridge IP address
        execute_command(ssh_client, f'/ip address set [/ip address find interface="Bridge1"] address="{lan_address}"')
        print(f"\nUpdated IP address {lan_address} on Bridge1.")
        output_file.write(f"\nUpdated IP address {lan_address} on Bridge1.\n")
        time.sleep(1)

        # Step 2: Update DHCP server network and gateway
        execute_command(ssh_client, f"/ip dhcp-server network set 0 address={dhcp_network} gateway={bridge_ip}")
        print(f"Updated DHCP network {dhcp_network} with gateway {bridge_ip}.")
        output_file.write(f"Updated DHCP network {dhcp_network} with gateway {bridge_ip}.\n")
        time.sleep(1)

        # Step 3: Update IP Pool range to the specified pool range
        execute_command(ssh_client, f"/ip pool set 0 ranges={dhcp_pool}")
        print(f"Updated DHCP pool range to {dhcp_pool}.")
        output_file.write(f"Updated DHCP pool range to {dhcp_pool}.\n")
        time.sleep(1)

        # Step 4: Configure IP tunnel with the remote address
        remote_ip = '43.252.198.121'  # Remote IP address for the tunnel
        execute_command(ssh_client, f"/interface ipip add name=To-DC remote-address={remote_ip}")
        print(f"Configured IP tunnel with remote address {remote_ip}.")
        output_file.write(f"Configured IP tunnel with remote address {remote_ip}.\n")
        time.sleep(1)

        # Step 5: Update NVR IP in NAT Rules
        execute_command(ssh_client, f"ip firewall nat set [/ip firewall nat find to-addresses=192.168.1.5] to-addresses={nvr_ip}")
        print(f"Configured NAT Rule {nvr_ip}.")
        output_file.write(f"Configured NAT Rule {nvr_ip}.\n")
        time.sleep(1)

        # Step 6: Update Masqurade
        execute_command(ssh_client, f'ip firewall nat set [/ip firewall nat find src-address="192.168.1.0/24"] src-address={dhcp_network}')
        print(f"Configured Masqurade Rule {dhcp_network}.")
        output_file.write(f"Configured Masqurade Rule {dhcp_network}.\n")
        time.sleep(1)

        # Step 7: Add Static Route (commented out)
        # execute_command(ssh_client, f'ip route add dst-address={dhcp_network} gateway="To-DC"')
        # print(f"Configured Static Route.")
        # output_file.write(f"Configured Static Route.\n")
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
        output_file.write("Script Added Successfully.\n")
        time.sleep(1)

        # Step 9: Configure Tunnel IP:
        execute_command(ssh_client, f'/ip address add address="{tunnel_ip}" interface=To-DC')
        print(f'Tunnel IP {tunnel_ip} configured on interface To-DC.')
        output_file.write(f'Tunnel IP {tunnel_ip} configured on interface To-DC.\n')
        time.sleep(1)

        # Step 10: Configure Identity:
        execute_command(ssh_client, f'/system identity set name="{link_name}"')
        print(f'Identity {link_name} set for Router {wan}.')
        output_file.write(f'Identity {link_name} set for Router {wan}.\n')
        time.sleep(1)

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

        # Fetch and print all configurations and NAT rules
        print(f"\nConfiguration summary for router {wan}:")
        output_file.write(f"\nConfiguration summary for router {wan}:\n")
        
        lan_address_output = execute_command(ssh_client, f'/ip address print where address="{lan_address}"')
        print(f" - IP address on Bridge1:\n{lan_address_output}\n")
        output_file.write(f" - IP address on Bridge1:\n{lan_address_output}\n")
        
        dhcp_network_output = execute_command(ssh_client, f"/ip dhcp-server network print")
        print(f" - DHCP Network:\n{dhcp_network_output}\n")
        output_file.write(f" - DHCP Network:\n{dhcp_network_output}\n")

        # Fetch and print the IP Pool range
        dhcp_pool_output = execute_command(ssh_client, f"/ip pool print")
        print(f" - DHCP Pool:\n{dhcp_pool_output}\n")
        output_file.write((f" - DHCP Pool:\n{dhcp_pool_output}\n"))

        # Fetch and print the IP tunnel settings
        tunnel_output = execute_command(ssh_client, "/interface ipip print")
        print(f" - IP Tunnel:\n{tunnel_output}\n")
        output_file.write(f" - IP Tunnel:\n{tunnel_output}\n")

        # Print NAT Rules
        nat_rules = execute_command(ssh_client, f"ip firewall nat print where to-addresses={nvr_ip}")
        print(f" - DST-NAT:\n{nat_rules}\n")
        output_file.write(f" - DST-NAT:\n{nat_rules}\n")

        # Print Masqurade Rule
        src_rules = execute_command(ssh_client, f'ip firewall nat print where src-address="{dhcp_network}"')
        print(f" - SRC-NAT:\n{src_rules}\n")
        output_file.write(f" - SRC-NAT:\n{src_rules}\n")

        # # Print Static Route:
        # static_route = execute_command(f'ip route print where gateway="To-DC"')
        # print(f" - Static-Route: {static_route}\n")
        #output_file.write(f" - Static-Route: {static_route}\n")

        # print script content:
        schedular = execute_command(ssh_client, '/system scheduler print')
        print(f" - Schedular: \n{schedular}\n")
        output_file.write(f" - Schedular: \n{schedular}\n")
        script_p = execute_command(ssh_client, '/system script print')
        print(f" - Script: \n{script_p}\n")
        output_file.write(f" - Script: \n{script_p}\n")
        e_mail = execute_command(ssh_client, '/tool e-mail print')
        print(f" - E-Mail: \n{e_mail}\n")
        output_file.write(f" - E-Mail: \n{e_mail}\n")
        dns = execute_command(ssh_client, '/ip dns print')
        print(f" - DNS: \n{dns}\n")
        output_file.write(f" - DNS: \n{dns}\n")
        clock = execute_command(ssh_client, '/system clock print')
        print(f" - Clock: \n{clock}\n")
        output_file.write(f" - Clock: \n{clock}\n")
        ntp = execute_command(ssh_client, '/system ntp client print')
        print(f" - NTP-Client: \n{ntp}\n")
        output_file.write(f" - NTP-Client: \n{ntp}\n")

        # Print Tunnel IP Config:
        tun_ip = execute_command(ssh_client, f'/ip address print where address="{tunnel_ip}"')
        print(f' - Tunnel IP: \n{tun_ip}\n')
        output_file.write(f' - Tunnel IP: \n{tun_ip}\n')

        # Print Router Identity:
        identity = execute_command(ssh_client, f'/system identity print')
        print(f' - Router Name is: \n{identity}\n')
        output_file.write(f' - Router Name is: \n{identity}\n')
        
        # Close the SSH connection
        ssh_client.close()
        print("#################################################################################################")
        print("#################################################################################################")
        output_file.write("#################################################################################################\n")
        output_file.write("#################################################################################################\n")

    except Exception as e:
        print(f"\nFailed to configure {wan}: {e}\n")
        output_file.write(f"\nFailed to configure {wan}: {e}\n")
        traceback.print_exc()
        output_file.write("\n" + traceback.format_exc())
        print("\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
        output_file.write("\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

    finally:
        # Ensure output file is properly closed when done
        output_file.close()

# Run the script with required parameters
link_name = "Sample_Router"
wan = "192.168.1.1"
bridge_ip = "192.168.88.1"
dhcp_network = "192.168.88.0/24"
dhcp_pool = "192.168.88.10-192.168.88.100"
nvr_ip = "192.168.1.5"
tunnel_ip = "10.1.1.1"
username = "admin"
password = "password"

# Call function to configure router
configure_router(link_name, wan, bridge_ip, dhcp_network, dhcp_pool, nvr_ip, tunnel_ip, username, password)
