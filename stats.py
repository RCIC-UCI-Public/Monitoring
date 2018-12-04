#!/usr/bin/env python

""" Runs function based on argument provided, generates XML output and other functions queries XML file instead of qmaster directly. """

from xml.etree import ElementTree
from pprint import pprint
from time import sleep
import argparse

def get_host_attri(host):
    """
    Gets the attributes of the hosts from the parsed xml object. 
    Generally unused, call this function for sanity checks.
    Works for both Python 2.6 and Python 2.7

    Returns example - 
    {'name': 'global'}
    {'name': 'admin.default.domain'}
    {'name': 'aquilah1.default.domain'}
    {'name': 'aquilah2.default.domain'}
    {'name': 'n001.default.domain'}
    .
    .
    .
    {'name': 'n127.default.domain'}
    """

    for h in host:
        print(h.attrib)

def get_hosts_details_list(xmlfile):
    """
    Parses results of qhost -q -xml XML file.
    Gets the list of hostvalues and queuevalues under individual hosts and generate dictionary.
    Works for both Python 2.6 and Python 2.7.
    """

    findall_hosts = []

    try:
        dom = ElementTree.parse(xmlfile)
    except Exception, e:
        print(e)
    else:
        # Find all hosts in dom.
        findall_hosts = dom.findall('host')

    cluster = {}
    for h in findall_hosts:
        # Create a key in cluster dictionary, named by each unique host in the cluster.
        cluster[h.attrib['name']] = {}
        # Loop through the list of hostvalues under host entity
        # hv is the memory element of the hostvalue (e.g. <Element 'hostvalue' at 0x10dd30c50>), hence we break the element down into two sections, hv.attrib['name'] (the name of the hostvalue) and hv.text (the value of the hostvalue), put these two values into a set, and put these sets into a list.
        # Example - [('arch_string', 'lx-amd64'), ('num_proc', '40'), ('m_socket', '2'), ('m_core', '20'), ('m_thread', '40'), ('np_load_avg', '0.32'), ('mem_total', '125.9G'), ('mem_used', '4.7G'), ('swap_total', '7.8G'), ('swap_used', '15.5M')]
        all_hostvalue = [(hv.attrib['name'], hv.text) for hv in h.findall('.//hostvalue')]
        # Next, we create a sub dictionary key call 'hostvalue' under the host key.
        cluster[h.attrib['name']]['hostvalue'] = {}
        # We loop through the hostvalue list and populate the values for the hostvalue key under the host key with the name of the hostvalue and the value of the hostvalue.
        for hv in all_hostvalue:
            cluster[h.attrib['name']]['hostvalue'][hv[0]] = hv[1]
        # Each host is usually assigned to 1 or more queue, here, we identify the complete list of queues, which each particular host can be a part of, or not, and create sub keys under the host key.
        all_queue = [q.attrib['name'] for q in h.findall('.//queue')]
        # Next, we loop through the whole list of qname from `all_queue`, and compare with the list of qname in h.findall('.//queue/queuevalue'), when there is a match (there's always a match), take the names and the values under matched qname and add to qname sub key.
        for qname in all_queue:
            cluster[h.attrib['name']][qname] = {}
            for qv in h.findall('.//queue/queuevalue'):
                if qname == qv.attrib['qname']:
                    cluster[h.attrib['name']][qname][qv.attrib['name']] = qv.text
    return cluster

def seek_heavy_load(xmlfile):
    """ 
    Passes XML file to get_hosts_details_list(), expects a dictionary.
    Checks load average of compute, interactive, login and io nodes and prints out nodes with load average "np_load_avg" greater than 0.8. 
    """

    hosts_lists = get_hosts_details_list(xmlfile)

    heavy_load = {}

    total_memory_used = 0
    total_memory      = 0
    total_sockets     = 0

    for node in hosts_lists.keys():
        # Omits out global.
        # Omits out Login nodes, admin nodes and head nodes.

        if node not in ('global', 'admin.default.domain', 'aquilah1.default.domain', 'aquilah2.default.domain'):
            
            # Check if node is down, as marked by a dash (-) in NLOAD, MEMUS and SWAPUS. 
            if (hosts_lists[node]['hostvalue']['mem_used']) == '-':
                pass
            else:
                # Get mem_used and mem_total. Convert it to float.
                if hosts_lists[node]['hostvalue']['mem_used'][-1:] == 'G':
                    memory_used = float(hosts_lists[node]['hostvalue']['mem_used'].rstrip("G"))*1000
                elif hosts_lists[node]['hostvalue']['mem_used'][-1:] == 'T':
                    memory_used = float(hosts_lists[node]['hostvalue']['mem_used'].rstrip("T"))*1000000
                else:
                    memory_used = float(hosts_lists[node]['hostvalue']['mem_used'].rstrip("M"))

                if hosts_lists[node]['hostvalue']['mem_total'][-1:] == 'G':
                    memory_total = float(hosts_lists[node]['hostvalue']['mem_total'].rstrip("G"))*1000
                elif hosts_lists[node]['hostvalue']['mem_total'][-1:] == 'T':
                    memory_total = float(hosts_lists[node]['hostvalue']['mem_total'].rstrip("T"))*1000000
                else:
                    memory_total = float(hosts_lists[node]['hostvalue']['mem_total'].rstrip("M"))
                total_memory_used += memory_used
                total_memory      += memory_total

                # Get np_load_avg(load average)
                np_load_avg = hosts_lists[node]['hostvalue']['load_avg']
                m_socket    = float( hosts_lists[node]['hostvalue']['m_socket'] )
                total_sockets += m_socket

                # Calculate memory (RSS) usage percentage.
                mem_used_percentage = (float(memory_used)/float(memory_total))*100
                
                print memory_used, memory_total, mem_used_percentage, np_load_avg, m_socket

                # Verbose printing of memory (RSS) usage.
                # print("{0}, {1:2.2f}%").format(node, mem_used_percentage)

                # If node has high load average AND high memory usage.
                if (float(np_load_avg) >= 0.010) and (mem_used_percentage >= 10.0):
                    hosts_lists[node]['hostvalue']['load_avg'] = "<font style=\"color:red;\">" + hosts_lists[node]['hostvalue']['load_avg']
                    hosts_lists[node]['hostvalue']['mem_used'] = "<font style=\"color:red;\">" + hosts_lists[node]['hostvalue']['mem_used']
                # If node has high load average ONLY.
                elif (float(np_load_avg) >= 0.010) and (mem_used_percentage < 10.0):
                    hosts_lists[node]['hostvalue']['load_avg'] = "<font style=\"color:red;\">" + hosts_lists[node]['hostvalue']['load_avg']
                    heavy_load[node] = hosts_lists[node]['hostvalue']
                # If node has high memory usage ONLY.
                elif (float(np_load_avg) < 0.010) and (mem_used_percentage >= 10.0):
                    hosts_lists[node]['hostvalue']['mem_used'] = "<font style=\"color:red;\">" + hosts_lists[node]['hostvalue']['mem_used']
                    heavy_load[node] = hosts_lists[node]['hostvalue']
                else:
                    pass

    print total_memory_used, total_memory, total_sockets

def seek_ooc_nodes(xmlfile):
    """
    Passes XML file to get_hosts_details_list(), expects a dictionary.
    For nodes which sgeexecd isn't running, np_load_avg is '-', this function checks for such instances.

    """

    # Passes XML file get_hosts_details_list() for parsing.
    hosts_lists = get_hosts_details_list(xmlfile)

    # Dictionary of out of circulation nodes.
    ooc_nodes = {}

    for node in hosts_lists.keys():
        # Omits out global.
        # Omits out Login nodes, admin nodes and head nodes.
        if node not in ('global', 'admin.default.domain', 'aquilah1.default.domain', 'aquilah2.default.domain'):

            # Get np_load_avg(load average)
            np_load_avg = hosts_lists[node]['hostvalue']['load_avg']

            # If value of  hosts_lists[node]['hostvalue']['np_load_avg'] is a dash (-).
            if (np_load_avg == '-'):
                ooc_nodes[node] = hosts_lists[node]['hostvalue']

    # Passes dictionary out to writeout to generate HTML file.
    #writeout.write_to_html('ooc',ooc_nodes)
    # If there are any nodes which are out of circulation, call send_email.py to send e-mail notification.
    #if len(ooc_nodes) > 0:
    #    send_email.ooc_email()
    #return True

def _argparse():
    """ Parse the argument if included or print help message. """

    import sys

    # Accepts 3 arguments, hl, ooc and cu.
    # cu is initiated to generate XML files.
    # ooc and hl reads cu-generated XML file.
    parser = argparse.ArgumentParser()
    parser.add_argument('-hl', '--heavyload', action = 'store_true', help = "Check compute nodes. Full command is \'qhost -q -xml\', used to check for nodes under heavy load (memory and load average).")
    parser.add_argument('-ooc', '--outofcirculation', action='store_true', help = "Check compute nodes for nodes which are either down or out of circulation.")
    parser.add_argument('-cu', '--checkuge', action = 'store_true', help = "Calls run_univa_commands to check UGE cluster. Generates a bunch of XML.")
    args = parser.parse_args()

    # If there are no arguments, print help message.
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    return args

def main():
    """
    Main function of check_uge.py.
    Calls _argparse to validate option (only one option), then calls run_univa_commands.py and run UNIVA commands on it, processes the generated XML file.
    """

    # List of commands and output XML files, this dictionary has two uses. 
    # 1. It gets passed to run_univa_commands.py to generate XML files 
    # 2. Based on the arguments, the script knows the location of the XML to get data for processing.

    dictofugecommands = {
    "qhost -q -xml": "/data/users/jtatar/Work/Monitoring/qhost-q.xml",
    "qstat -u \'*\' -xml": "/usr/local/bin/scripts/qstat_all_users.xml"
    }

    # Pass the arguments to _argparse for validation.
    directive = _argparse()

    # Once arguments are validated, calls corresponding function.
    if (vars(directive)['checkuge'] == True):
        for ugecommand in dictofugecommands.iteritems():
            run_univa_commands.run_univa_commands(ugecommand)
    elif (vars(directive)['heavyload'] == True):
        seek_heavy_load(dictofugecommands["qhost -q -xml"])
    elif vars(directive)['outofcirculation'] == True:
        seek_ooc_nodes(dictofugecommands["qhost -q -xml"])
    else:
        print(vars(directive))

if __name__ == '__main__':
    main()
