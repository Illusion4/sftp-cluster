# -*- mode: ruby -*-
# vi: set ft=ruby :

hosts = {
  "sftp1" => "192.168.88.10",
  "sftp2" => "192.168.88.11",
  "sftp3" => "192.168.88.12",
}

host_key_path = File.expand_path("~/.ssh/vagrant_host_key")
host_pub_path = host_key_path + ".pub"

unless File.exist?(host_key_path) && File.exist?(host_pub_path)
  puts "[+] Generating HOST SSH key at #{host_key_path}"
  system("ssh-keygen -t rsa -b 4096 -f #{host_key_path} -N \"\"")
end

sftp_pub_keys = {}
hosts.each do |name, ip|
  sftp_key_path = File.expand_path("~/.ssh/sftp_user_key_#{name}")
  sftp_pub_path = sftp_key_path + ".pub"
  
  unless File.exist?(sftp_key_path) && File.exist?(sftp_pub_path)
    puts "[+] Generating SFTP user key for #{name} at #{sftp_key_path}"
    system("ssh-keygen -t rsa -b 4096 -f #{sftp_key_path} -N \"\"")
  end
  sftp_pub_keys[name] = File.read(sftp_pub_path)
end

combined_sftp_auth = File.expand_path("~/.ssh/sftp_combined_authorized_keys")
File.open(combined_sftp_auth, 'w') do |f|
  sftp_pub_keys.values.each { |pub| f.puts(pub) }

  if File.exist?(host_pub_path)
    f.puts File.read(host_pub_path)
  end
end

Vagrant.configure("2") do |config|
  config.vm.box = "hashicorp/bionic64"

  hosts.each do |name, ip|
    config.vm.define name do |machine|
      machine.vm.network :private_network, ip: ip
      machine.vm.provider "virtualbox" do |vb|
        vb.name = name
        vb.gui = false
        vb.memory = "1024"
        vb.cpus = 2
      end
      machine.ssh.insert_key = false
      machine.ssh.private_key_path = [host_key_path, "~/.vagrant.d/insecure_private_key"]

      machine.vm.provision "file",
        source: host_pub_path,
        destination: "/home/vagrant/.ssh/authorized_keys"

      machine.vm.provision "file",
        source: File.expand_path("~/.ssh/sftp_user_key_#{name}"),
        destination: "/tmp/sftp_key"

      machine.vm.provision "file",
        source: combined_sftp_auth,
        destination: "/tmp/sftp_authorized_keys"

      machine.vm.provision "file", source: "scripts", destination: "/tmp/"
      machine.vm.provision "shell", path: "provision.sh"
    end
  end
end

