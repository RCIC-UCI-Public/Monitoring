#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import socket
from subprocess import Popen,PIPE
import sys
import time
import os
import urllib2

#os.system("source /etc/profile.d/sge.sh")

try:
    cluster_name = os.environ["SGE_CELL"]
except KeyError:
    print "SGE_CELL environment variable not found. Please source the SGE settings file"
    sys.exit(1)

cluster_name = "HPC"

# define which complex value you use for memory reservation
# typical values are h_vmem or m_mem_free
memory_complex_value = "h_rss"
    
# InfluxDB
INFLUXDB_SERVER = "192.5.19.66"
INFLUXDB_PORT = 8086
INFLUXDB_DBNAME = 'sge'

def main():

    now = int(time.time())

    #parse_qstatgc()
    slots_by_host   = parse_qstat_f_ext()
    jobs,pjobs      = parse_qstat()
    hosts           = parse_qhost()
    jobs_usage      = get_used_resources_by_jobs()
    #print jobs_usage
    #print len(jobs_usage)
    #print hosts 
    #print jobs
    lines = []

    #print jobs 
    #print get_running_jobs( jobs )
    #print get_pending_jobs( jobs )
    #print get_stopped_jobs( jobs )
    #print get_finished_jobs( jobs )

    users_list              = get_users_with_running_jobs(jobs)
    pusers_list             = get_users_with_pending_jobs(pjobs)
    slots_by_user           = get_slots_by_user(users_list, jobs)
    jobs_by_user            = get_running_jobs_by_user(users_list, jobs)
    pjobs_by_user           = get_pending_jobs_by_user(pusers_list, pjobs)

    print pusers_list

    projects_list   = get_projects_with_running_jobs(jobs)
    slots_by_project= get_slots_by_project(projects_list, jobs)
    jobs_by_project = get_running_jobs_by_project(projects_list, jobs)

    # queues  - list of queues with running jobs
    # pqueues - list of queues with pending jobs
    queues,pqueues  = get_queues_with_running_jobs(jobs)
    slots_by_queue  = get_slots_by_queue(queues, jobs)
    jobs_by_queue   = get_running_jobs_by_queue(queues, jobs)
    #pjobs_by_queue  = get_pending_jobs_by_queue(pqueues, pjobs)
    #print pjobs
#, pjobs, pjobs_by_queue

    #print queues
    #print slots_by_queue
    #print jobs_by_queue

    io_by_users = get_io_usage_by_user(users_list, jobs)
    #print io_by_users

    reserved_mem_by_user = get_reserved_memory_by_user(users_list, jobs)
    #print reserved_mem_by_user
    used_mem_by_user = get_used_rss_memory_by_user(users_list, jobs_usage)
    #print used_mem_by_user

    for k,v in slots_by_host.items():
        for l in v:
            for tp in l:
                if tp[0] == 'slots_used':
                    slots_used = tp[1]
                if tp[0] == 'slots_resv':
                    slots_resv = tp[1]
                if tp[0] == 'slots_total':
                    slots_total = tp[1]

            uvalues = ("slots_used", "cluster="+cluster_name, "hostname="+k,\
                                    "value_int="+str(slots_used)+"i", (999))
            rvalues = ("slots_resv", "cluster="+cluster_name, "hostname="+k,\
                                    "value_int="+str(slots_resv)+"i", (999))
            tvalues = ("slots_total", "cluster="+cluster_name, "hostname="+k,\
                                    "value_int="+str(slots_total)+"i", (999))

            uvalues = '{0},{1},{2} {3} {4}'.format(*uvalues)
            rvalues = '{0},{1},{2} {3} {4}'.format(*rvalues)
            tvalues = '{0},{1},{2} {3} {4}'.format(*tvalues)

            lines.append( uvalues )
            lines.append( rvalues )
            lines.append( tvalues )

    for i in slots_by_user:
        user = i[0]
        slots = i[1]
        values = ("slots", "cluster="+cluster_name, "user="+user, "value_int="+str(slots)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
    #for i in slots_by_project:
     #   project = i[0]
      #  slots = i[1]
       # values = ("slots", "cluster="+cluster_name, "project="+project, "value_int="+str(slots)+"i", str(now))
     #   values = '{0},{1},{2} {3} {4}'.format(*values)
      #  lines.append((values))
    for i in slots_by_queue:
        queue = i[0]
        #queue = queue.replace(".","_")
        slots = i[1]
        values = ("slots", "cluster="+cluster_name, "queue="+queue, "value_int="+str(slots)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
    
    for i in jobs_by_user:
        user = i[0]
        jobs = i[1]
        values = ("jobs", "cluster="+cluster_name, "user="+user, "value_int="+str(jobs)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))

    for i in pjobs_by_user:
        user    = i[0]
        pjobs   = i[1]
        # upjobs - user pending jobs
        values = ("upjobs", "cluster="+cluster_name, "user="+user,\
                                        "value_int="+str(pjobs)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values)) 

    #for i in jobs_by_project:
     #   project = i[0]
      #  jobs = i[1]
       # values = ("jobs", "cluster="+cluster_name, "project="+project, "value_int="+str(jobs)+"i", str(now))
        #values = '{0},{1},{2} {3} {4}'.format(*values)
        #lines.append((values))
    
    for i in jobs_by_queue:
        queue = i[0]
        #queue = queue.replace(".","_")
        jobs = i[1]
        values = ("jobs", "cluster="+cluster_name, "queue="+queue, "value_int="+str(jobs)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))

#    for i in pjobs_by_queue:
#        queue   = i[0]
#        jobs    = i[1]

#        values  = ("pjobs", "cluster="+cluster_name, "queue="+queue,\
                                        #"value_int="+str(jobs)+"i", str(now))
#        values  = '{0},{1},{2} {3} {4}'.format(*values)
#        lines.append((values))

    for i in reserved_mem_by_user:
        user = i[0]
        reserved_mem = i[1]
        values = ("reserved_mem", "cluster="+cluster_name, "user="+user, "value_int="+str(reserved_mem)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
    
    for i in used_mem_by_user:
        user = i[0]
        used_mem = i[1]
        values = ("used_mem", "cluster="+cluster_name, "user="+user, "value_int="+str(used_mem)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
    
    for i in io_by_users:
        user = i[0]
        io = i[1]
        values = ("io", "cluster="+cluster_name, "user="+user, "value="+str(io), str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
   
    used_mem_by_host = get_used_mem_by_host(hosts)
    cores_by_host = get_num_cores_by_host( hosts )

    #print used_mem_by_host
    for i in used_mem_by_host:
        hostname = i[0].split('.')[0]
        used_mem = i[1]
        values = ("qhost_used_mem", "cluster="+cluster_name, "hostname="+hostname, "value_int="+str(used_mem)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))
    
    used_swap_by_host = get_used_swap_by_host(hosts)
    #print used_swap_by_host
    for i in used_swap_by_host:
        hostname = i[0].split('.')[0]
        used_swap = i[1]
        values = ("qhost_used_swap", "cluster="+cluster_name, "hostname="+hostname, "value_int="+str(used_swap)+"i", str(now))
        values = '{0},{1},{2} {3} {4}'.format(*values)
        lines.append((values))

    used_resources = get_used_resources_by_jobs()
    used_rss = 0
    max_rss = 0
    for job in used_resources:
        if 'rss' in job:
            used_rss += job['rss']
        if 'maxrss' in job:
            max_rss += job['maxrss']
    #print used_rss    
    #print max_rss
    
    #used_mem = 0
    #for i in used_mem_by_host:
        #used_mem += i[1] 
    #print used_mem

    #get_used_rss_memory_by_user(users_list, jobs_usage)
    message = '\n'.join(lines) + '\n'
    #print message
    send_to_influxdb(message)
    #send_to_graphite(message)


def get_running_jobs(jobs):
    " returns an integer with total amount of running jobs "
    running_jobs = 0
    for job in jobs:
        if job['state'] == 'r':
            running_jobs += 1
    return running_jobs


def get_pending_jobs( jobs ):
    " returns an integer with total amount of pending jobs "
    pending_jobs = 0
    for job in jobs:
        if job['state'] == 'qw':
            pending_jobs += 1

    return pending_jobs


def get_finished_jobs( jobs ):
    " returns an integer with total amount of completed jobs "
    finished_jobs = 0
    for job in jobs:
        if job['state'] == 'z':
            finished_jobs += 1

    return finished_jobs


def get_stopped_jobs( jobs ):
    " returns an integer with total amount of stopped jobs "
    stopped_jobs = 0

    for job in jobs:
        if job['state'] == 's':
            stopped_jobs += 1

    return stopped_jobs


def get_used_slots(jobs):
    " return an integer with total amount of used slots"
    used_slots = 0
    for job in jobs:
        if job['state'] == 'r':
            used_slots += int(job['slots'])
    return used_slots


def get_users_with_running_jobs(jobs):
    " returns a list with all the users who have running jobs"
    users   = []
    for job in jobs:
        if job['state'] == 'r' and job['JB_owner'] not in users:
            users.append(job['JB_owner'])

    return users


def get_users_with_pending_jobs(jobs):
    " returns a list with all the users who have running jobs"
    pusers  = []
    for job in jobs:
        if job['JB_owner'] not in pusers and (job['state'] == 'qw' or\
                                              job['state'] == 'hqw'):
            pusers.append(job['JB_owner'])

    return pusers




def get_projects_with_running_jobs(jobs):
    " returns a list with all the projects which have running jobs"
    projects = []
    for job in jobs:
        if job['state'] == 'r' and job['JB_project'] not in projects:
            projects.append(job['JB_project'])
    return projects


def get_slots_by_user(users_list, jobs):
    " returns a list of tuples in format: (username, used_slots)"
    slots_by_user = []
    for user in users_list:
        slots = 0
        for job in jobs:
            if job['JB_owner'] == user and job['state'] == 'r':
                slots += int(job['slots'])
        slots_by_user.append((user,slots))
    return slots_by_user


def get_running_jobs_by_user(users_list, jobs):
    " returns a list of tuples in format: (username, running_jobs)"
    jobs_by_user = []
    for user in users_list:
        running_jobs = 0
        for job in jobs:
            if job['JB_owner'] == user and job['state'] == 'r':
                running_jobs += 1
        jobs_by_user.append((user,running_jobs))
    return jobs_by_user


def get_pending_jobs_by_user(users_list, jobs):
    " returns a list of tuples in format: (username, pending_jobs)"
    jobs_by_user = []
    for user in users_list:
        pending_jobs = 0
        for job in jobs:
            if job['JB_owner'] == user and (job['state'] == 'qw' or\
                                            job['state'] == 'hqw'):
                pending_jobs += 1
        jobs_by_user.append((user,pending_jobs))

    return jobs_by_user


def get_slots_by_project(projects_list, jobs):
    " returns a list of tuples in format: (project, slots)" 
    slots_by_project = []
    for project in projects_list:
        slots = 0
        for job in jobs:
            if job['JB_project'] == project and job['state'] == 'r':
                slots += int(job['slots'])
        slots_by_project.append((project, slots))
    return slots_by_project


def get_running_jobs_by_project(projects_list, jobs):
    " returns a list of tuples in format: (project, running_jobs)"
    jobs_by_project = []
    for project in projects_list:
        running_jobs = 0
        for job in jobs:
            if job['JB_project'] == project and job['state'] == 'r':
                running_jobs += 1
        jobs_by_project.append((project,running_jobs))
    return jobs_by_project


def get_queues_with_running_jobs(jobs):
    queues  = []
    pqueues = []
    for job in jobs:
        job_queue = job['queue_name'].split('@')[0]
        if job_queue not in queues and job['state'] == 'r':
            queues.append(job_queue)
        if job_queue not in pqueues and (job['state'] == 'qw' or\
                                         job['state'] == 'hqw'):
            pqueues.append(job_queue)
    return queues, pqueues

def get_slots_by_queue(queues_list, jobs):
    slots_by_queue = []
    for queue in queues_list:
        slots = 0
        for job in jobs:
            job_queue = job['queue_name'].split('@')[0]
            if queue == job_queue and job['state'] == 'r':
                slots += int(job['slots'])
        slots_by_queue.append((queue, slots))
    return slots_by_queue

def get_running_jobs_by_queue(queues, jobs):
    jobs_by_queue = []
    for queue in queues:
        running_jobs = 0
        for job in jobs:
            job_queue = job['queue_name'].split('@')[0]
            if queue == job_queue and job['state'] == 'r':
                running_jobs += 1
        jobs_by_queue.append((queue, running_jobs))
    return jobs_by_queue

def get_pending_jobs_by_queue(queues, jobs):
    " returns and integer with number of waiting jobs"
    pjobs_by_queue = []

    for q in queues:
        pjobs = 0
        for job in jobs:
            pjob_queue = job['queue_name'].split('@')[0]

            if q == pjob_queue and (job['state'] == 'qw' or job['state'] == 'hqw'): 
                pjobs += 1
        pjobs_by_queue.append((q, pjobs))

    return pjobs_by_queue



def get_io_usage_by_user(users_list, jobs):
    " returns a list of tuples in format: (username, io_usage)"
    io_by_user = []
    for user in users_list:
        user_io_usage = 0.0
        for job in jobs:
            if job['JB_owner'] == user and job['state'] == 'r':
                if 'io_usage' in job:
                    user_io_usage += float(job['io_usage'])
        io_by_user.append((user, user_io_usage))
    return io_by_user

def get_total_io_usage(jobs):
    total_io = 0.0
    for job in jobs:
        if job['state'] == 'r':
            if 'io_usage' in job:
                total_io += float(job['io_usage'])
    return total_io

def get_used_rss_memory_by_user(users_list, jobs):
    """ returns a list of tuples in the format: (user, used_mem)
    used_mem is the rss value reported by 'qstat -j *' for running jobs"""
    mem_by_user = []
    for user in users_list:
        user_used_mem = 0
        for job in jobs:
            if 'JB_owner' in job and 'rss' in job:
                if job['JB_owner'] == user:
                    user_used_mem += job['rss']
        mem_by_user.append((user,user_used_mem))
    return mem_by_user

def get_reserved_memory_by_user(users_list, jobs):
    """ Returns a list of tuples in format: (username, reserved_mem_by_user).
        reserved_mem_by_user is in megabytes
        This function assumes that the memory reservation is by-core and that's
        why job_reserved_mem is multiplied by number of slots """
    mem_by_user = []
    for user in users_list:
        user_reserved_mem = 0
        for job in jobs:
            job_reserved_mem = 0
            if job['JB_owner'] == user and job['state'] == 'r':
                requested_mem = 'requested_%s' % (memory_complex_value)
                if requested_mem in job:
                    # get reserved memory (which can be in format 100M or 2G) in bytes
                    job_reserved_mem = human2bytes(job[requested_mem])
                    # multiply reserved memory by number of slots
                    job_reserved_mem = job_reserved_mem * int(job['slots'])
                    # convert bytes to megabytes and remove decimals
                    job_reserved_mem = int((float(job_reserved_mem)/float(1024))/float(1024))
                    user_reserved_mem += job_reserved_mem
        mem_by_user.append((user, user_reserved_mem))
    return mem_by_user

def get_total_reserved_memory(jobs):
    """ Returns total reserved_memory. reserved_memory is in megabytes
        This function assumes that the memory reservation is by-core and that's
        why job_reserved_mem is multiplied by number of slots """
    total_reserved_mem = 0
    for job in jobs:
        if job['state'] == 'r':
            requested_mem = 'requested_%s' % (memory_complex_value)
            if requested_mem in job:
                #print job[requested_mem]
                # get reserved memory (which can be in format 100M or 2G) in bytes
                job_reserved_mem = human2bytes(job[requested_mem])
                # multiply reserved memory by number of slots
                job_reserved_mem = job_reserved_mem * int(job['slots'])
                # convert bytes to megabytes and remove decimals
                job_reserved_mem = int((float(job_reserved_mem)/float(1024))/float(1024))
                total_reserved_mem += job_reserved_mem
    return total_reserved_mem

def get_used_mem_by_host(hosts):
    """ Returns a list of tuples in format: (host, used_mem).
        used_mem is in megabytes """
    mem_by_host = []
    for host in hosts:
        if 'mem_used' in host:
            if host['mem_used'] == '0.0' or host['mem_used'] == '-':
                host_used_mem = 0
                continue
            # get used memory (which can be in format 100M or 2G) in bytes
            host_used_mem = human2bytes(host['mem_used'])
            # convert bytes to megabytes and remove decimals
            host_used_mem = int((float(host_used_mem)/float(1024))/float(1024))
        mem_by_host.append((host['hostname'], host_used_mem))
    return mem_by_host


def get_num_cores_by_host( hosts ):
    """ Returns a list of tuples in format: (host, m_core)."""

    cores_by_host = []

    for host in hosts:
        if 'm_core' in host:
            cores_by_host.append((host['hostname'], host['m_core']))
            #print host['m_core']

    return cores_by_host


def get_used_swap_by_host(hosts):
    """ Returns a list of tuples in format: (host, used_swap).
        used_swap is in megabytes """
    swap_by_host = []
    for host in hosts:
        if 'swap_used' in host:
            #print 'swap_used'
            #print host['swap_used']
            if host['swap_used'] == '0.0' or host['swap_used'] == '-':
                host_used_swap = 0
                continue
            # get used swap (which can be in format 100M or 2G) in bytes
            host_used_swap = human2bytes(host['swap_used'])
            # convert bytes to megabytes and remove decimals
            host_used_swap = int((float(host_used_swap)/float(1024))/float(1024))
        swap_by_host.append((host['hostname'], host_used_swap))
    return swap_by_host


def parse_qstatgc():
    " returns a list of dictionaries. Each dictionary contains the info for host"

    qstatgc_xml_out = Popen(["qstat", "-g", "c", "-xml"], stdout=PIPE).communicate()[0]
    tree = ET.ElementTree(ET.fromstring(qstatgc_xml_out))
    root = tree.getroot( )

    queue_xml_elements = root.findall("./cluster_queue_summary")

    total_slots = 0
    total_used  = 0
    total_avail = 0

    for el in queue_xml_elements:

        for i in el.getiterator():

            if i.tag == "total":
                total_slots += int( i.text ) 

            if i.tag == "used":
                total_used  += int( i.text )
    
            if i.tag == "available":
                total_avail += int( i.text )

    print total_slots, total_used, total_avail


def parse_qstat_f_ext( ):

    findall_qs = []

    qstatfext_xml_el = Popen(["qstat", "-f", "-ext", "-xml"], stdout=PIPE).communicate()[0]
    tree = ET.ElementTree(ET.fromstring(qstatfext_xml_el))
    root = tree.getroot( )

    findall_qs = root.findall( './queue_info/Queue-List' )

    from collections import defaultdict
    #compute_info = dict() 
    compute_info = defaultdict(list)

    for q in findall_qs:

        hostnm      = None
        used        = 0
        resv        = 0
        total       = 0

        compute = []

        for i in q.getiterator():

            if i.tag == "name":
                hostnm = i.text.split( "@", 1 )[1]
            if i.tag == "slots_used":
                used = int(i.text)
            if i.tag == "slots_resv":
                resv = int(i.text)
            if i.tag == "slots_total":
                total = int(i.text) 

            compute = [('hostname', hostnm), ('slots_used', used),\
                                ('slots_resv', resv), ('slots_total', total)]

        if hostnm in compute_info:
            for k,v in compute_info.items():
                for l in v:
                    for tp in l:
                        if tp[0] == "slots_used":
                            sused = int(tp[1])
                            if used > sused:
                                compute_info[hostnm][0] = compute

        else:
            compute_info[hostnm].append(compute)

    return compute_info
    #print compute_info['compute-4-65.local']


def parse_qstat():
    " returns a list of dictionaries. Each dictionary contains the info for a job"

    qstat_xml_output = Popen(["qstat", "-s", "rpsz", "-ext", "-g", "d", "-u", "*", "-r", "-xml"], stdout=PIPE).communicate()[0]
    tree = ET.ElementTree(ET.fromstring(qstat_xml_output))
    root = tree.getroot()

    # Running jobs
    job_xml_elements    = root.findall("./queue_info/job_list")
    # Jobs not in running state
    pjob_xml_elements   = root.findall( "./job_info/job_list" )    

    all_jobs_info   = []
    all_pjobs_info  = []

    for job in job_xml_elements:
        job_info = {}

        for i in job.getiterator():
            if i.tag == "requested_pe":
                job_info[i.tag] = i.attrib['name']
                continue
            if i.tag == "granted_pe":
                job_info[i.tag] = i.attrib['name']
                continue
            if i.tag == "hard_request":
                job_info["requested_" + str(i.attrib['name'])] = i.text
                continue
            job_info[i.tag] = i.text

        del job_info['job_list']
        all_jobs_info.append(job_info)

    for pjob in pjob_xml_elements:
        pjob_info = {}

        for i in pjob.getiterator():
            if i.tag == "requested_pe":
                pjob_info[i.tag] = i.attrib['name']
                continue
            if i.tag == "granted_pe":
                pjob_info[i.tag] = i.attrib['name']
                continue
            if i.tag == "hard_request":
                pjob_info["requested_" + str(i.attrib['name'])] = i.text
                continue
            pjob_info[i.tag] = i.text

        del pjob_info['job_list']
        all_pjobs_info.append(pjob_info)


    return all_jobs_info, all_pjobs_info

def get_used_resources_by_jobs():
    """ parse "qstat -j '*'" to get used resources for jobs. It returns a list of dictionaries. Each dictionary
    has the info for a job """

    qstat_xml_output = Popen(["qstat", "-s", "r", "-ext", "-g", "d", "-u", "*", "-r", "-j", "*", "-xml"], stdout=PIPE).communicate()[0]
    tree = ET.ElementTree(ET.fromstring(qstat_xml_output))
    root = tree.getroot()

    job_xml_elements = root.findall("./djob_info/element")
    running_jobs_usage = []

    for job in job_xml_elements:
        job_info = {}
        for i in job.getiterator():
            if i.tag == 'JB_owner':
                job_info['JB_owner'] = i.text
                continue
            if i.tag == 'JB_job_number':
                job_info['job_number'] = i.text
                continue
            if i.tag == 'JAT_task_number':
                job_info['job_task'] = i.text
                continue
            if i.tag == 'JAT_scaled_usage_list':
                usage_events = i.findall("./Events/")
                for child in usage_events:
                    resource_name = child.findall("./UA_name")[0].text
                    resource_usage = child.findall("./UA_value")[0].text
                    job_info[resource_name] = resource_usage
                    continue
            if 'job_number' in job_info and 'job_task' in job_info:
                job_info['jobid'] = job_info['job_number'] + "." + job_info['job_task']
            #print job_info
            #job_info
        running_jobs_usage.append(job_info)
    
    # normalize all the memory values to megabytes without decimals
    for job in running_jobs_usage:
        for name in 'vmem', 'maxvmem', 'rss', 'pss', 'smem', 'pmem', 'maxrss', 'maxpss':
            if name in job:
                job[name] = int((float(job[name])/float(1024))/float(1024))

    return running_jobs_usage
        
def parse_qhost():
    " returns a list of dictionaries. Each dictionary contains the info for a host"

    qhost_xml_output = Popen(["qhost", "-xml"], stdout=PIPE).communicate()[0]
    tree = ET.ElementTree(ET.fromstring(qhost_xml_output))
    root = tree.getroot()

    hosts_xml_elements = root.findall("./host")

    all_hosts_info = []

    for host in hosts_xml_elements:
        host_info = {}
        for i in host.getiterator():
            # first output from XML is just global info. We skip it
            if i.attrib['name'] == 'global':
                continue
            if i.text == '-':
                continue

            # if the xml tag is 'host' we fetch the machine hostname
            if i.tag == 'host':
                host_info['hostname'] = i.attrib['name']
            
            # if xml tag is 'hostvalue' we fetch the info 
            if i.tag == 'hostvalue':
                host_info[i.attrib['name']] = i.text

        # we verify that host_info is not empty because the first xml entry
        # generates a empty dict
        if host_info:
            all_hosts_info.append(host_info)

    return all_hosts_info
 
def send_to_graphite(message):
    sock = socket.socket()
    try:
        sock.connect( (CARBON_SERVER,CARBON_PORT) )
    except:
        print "Couldn't connect to %(server)s on port %(port)d " % { 'server':CARBON_SERVER, 'port':CARBON_PORT }
        sys.exit(1)
    #print message
    sock.send(message)

def send_to_influxdb(message):
    """ send metrics to influxdb """
    try:
        req = urllib2.Request('http://%s:%s/write?db=%s&u=%s&p=%s&precision=s' % (INFLUXDB_SERVER, INFLUXDB_PORT, INFLUXDB_DBNAME, INFLUXDB_USER, INFLUXDB_PASSWD))
        print INFLUXDB_SERVER, INFLUXDB_PORT, INFLUXDB_DBNAME, INFLUXDB_USER, INFLUXDB_PASSWD
        req.add_data(message)
        res=urllib2.urlopen(req)

    except (urllib2.HTTPError,urllib2.URLError) as e:
        print 'error connecting to influxdb'
        print e


def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.

      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776

      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """

    SYMBOLS = {
        'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
        'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                           'zetta', 'iotta'),
        'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                           'zebi', 'yobi'),
    }

    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


if __name__ == "__main__":
    main()

