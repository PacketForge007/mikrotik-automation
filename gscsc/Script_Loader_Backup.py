import paramiko

# MikroTik router credentials
host = "192.168.19.150"  # Replace with your MikroTik router IP address
port = 22  # SSH port (default is 22)
username = "admin"  # Replace with your MikroTik username
password = "admin"  # Replace with your MikroTik password

def load_script_to_router():
    try:
        # Create an SSH client instance
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the MikroTik router
        print(f"Connecting to {host}...")
        client.connect(host, port=port, username=username, password=password)

        # # Format the SCRIPT_CONTENT for MikroTik's source command
        # formatted_script_content = SCRIPT_CONTENT.replace("\n", "\r\n").replace('"', '\\"')

        # Add the script to MikroTik
        cmd1 = 'system scheduler add interval=1w20m name="E-Mail Backup" on-event=BackupMail policy=ftp,reboot,read,write,policy,test,password,sniff,sensitive,romon start-date=sep/30/2020 start-time=11:52:18'
        print("Adding script to MikroTik router...")
        script1 = '/system backup save name=email'
        script2 = ':delay 10s'
        script3 = '/export file=GSCSC_ARAVALLI_45MB_274.rsc'
        script4 = ':delay 10s'
        script5 = '/tool e-mail send to=support.ahmedabad@gtpl.net cc=amit.patel@gtpl.net subject=([/system identity get name].\\" Backup\\") file=GSCSC_ARAVALLI_45MB_274.rsc'
        script6 = ':delay 40s'
        script7 = ':log info \\"Backup e-mail sent.\\"'
        add_script_command = f'system script add dont-require-permissions=no name=BackupMail owner=Girish policy=ftp,reboot,read,write,policy,test,password,sniff,sensitive,romon source="{script1}\\r\\ \\n{script2}\\r\\ \\n{script3}\\r\\ \\n{script4}\\r\\ \\n{script5}\\r\\ \\n{script6}\\r\\ \\n{script7}"'
        cmd2 = '/tool e-mail set server=mail.gtpl.net from=backup.epcrouter@gtpl.net password=BAckUP#EPC#Router#062024 port=587 tls=yes user=backup.epcrouter'
        cmd3 = '/ip dns set servers=8.8.8.8,8.8.4.4,2001:4860:4860::8888,2001:4860:4860::8844'
        cmd4 = '/system clock manual set time-zone=+05:30'
        cmd5 = '/system ntp client set enabled=yes servers=27.116.54.34'

        # Execute the command to add the script
        stdin, stdout, stderr = client.exec_command(cmd1)
        stdin, stdout, stderr = client.exec_command(add_script_command)
        stdin, stdout, stderr = client.exec_command(cmd2)
        stdin, stdout, stderr = client.exec_command(cmd3)
        stdin, stdout, stderr = client.exec_command(cmd4)
        stdin, stdout, stderr = client.exec_command(cmd5)

        # Read and print output or error messages
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            print("Script added successfully.")
            print(output)
        if error:
            print("Error adding script:")
            print(error)

        # Close the SSH connection
        client.close()
        print("Connection closed.")
    
    except Exception as e:
        print(f"Error: {e}")
        client.close()

if __name__ == "__main__":
    load_script_to_router()
