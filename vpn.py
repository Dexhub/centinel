#!/usr/bin/python
# Ben Jones bjones99@gatech.edu
# Georgia Tech Fall 2014
#
# vpn.py: a top level interface to commands to run VPNs on a VM as
# different clients. The use case is allowing us to measure from more
# places.

import argparse
import os
import os.path

import centinel.backend
import centinel.client
import centinel.config
import centinel.openvpn
import centinel.hma

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth-file', '-u', dest='authFile',
                        help=("File with HMA username on first line, \n"
                              "HMA password on second line"))
    parser.add_argument('--create-hma-configs', dest='createHMA',
                        action="store_true",
                        help='Create the openvpn config files for HMA')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--directory", "-d", dest='directory',
                       help="Directory with experiments, config files, etc.")
    createConfHelp = ("Create configuration files for the given "
                      "openvpn config files so that we can treat each "
                      "one as a client. The argument should be a "
                      "directory with a subdirectory called openvpn "
                      "that contains the openvpn config files")
    group.add_argument('--create-config', '-c', help=createConfHelp,
                       dest='createConfDir')
    return parser.parse_args()


def scan_vpns(directory, authFile):
    """For each VPN, check if there are experiments and scan with it if
    necessary

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)

    """

    # iterate over each VPN
    vpnDir  = return_abs_path(directory, "vpns")
    confDir = return_abs_path(directory, "configs")
    authFile = return_abs_path(".", authFile)
    vpn = centinel.openvpn.OpenVPN()
    for filename in os.listdir(confDir):
        vpnConfig = os.path.join(vpnDir, filename)
        centConfig = os.path.join(confDir, filename)
        vpn.start(vpnConfig, timeout=30, authFile=authFile)
        if not vpn.started:
            vpn.stop()
            continue
        # now that the VPN is started, get centinel to process the VPN
        # stuff and sync the results
        config = centinel.config.Configuration()
        config.parse_config(centConfig)
        client = centinel.client.Client(config.params)
        client.setup_logging()
        client.run()
        centinel.backend.sync(config.params)
        vpn.stop()


def return_abs_path(directory, path):
    """Unfortunately, Python is not smart enough to return an absolute
    path with tilde expansion, so I writing functionality to do this

    """
    directory = os.path.expanduser(directory)
    return os.path.abspath(os.path.join(directory, path))


def create_config_files(directory):

    """For each VPN file in directory/vpns, create a new configuration
    file and all the associated directories

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    -----results (contains the results)

    """
    vpnDir  = return_abs_path(directory, "vpns")
    confDir = return_abs_path(directory, "configs")
    os.mkdir(confDir)
    homeDirs = return_abs_path(directory, "home")
    os.mkdir(homeDirs)
    for filename in os.listdir(vpnDir):
        configuration = centinel.config.Configuration()
        # setup the directories
        homeDir = os.path.join(homeDirs, filename)
        os.mkdir(homeDir)
        configuration.params['user']['centinel_home'] = homeDir
        expDir = os.path.join(homeDir, "experiments")
        os.mkdir(expDir)
        configuration.params['dirs']['experiments_dir'] = expDir
        dataDir = os.path.join(homeDir, "data")
        os.mkdir(dataDir)
        configuration.params['dirs']['data_dir'] = dataDir
        resDir = os.path.join(homeDir, "results")
        os.mkdir(resDir)
        configuration.params['dirs']['results_dir'] = resDir

        logFile = os.path.join(homeDir, "centinel.log")
        configuration.params['log']['log_file'] = logFile
        loginFile = os.path.join(homeDir, "login")
        configuration.params['server']['login_file'] = loginFile

        confFile = os.path.join(confDir, filename)
        configuration.write_out_config(confFile)


if __name__ == "__main__":
    args = parse_args()

    if args.createConfDir:
        if args.createHMA:
            hmaDir = return_abs_path(args.createConfDir, "vpns")
            centinel.hma.create_config_files(hmaDir)
        # create the config files for the openvpn config files
        create_config_files(args.createConfDir)
    else:
        scan_vpns(args.directory, args.authfile)
