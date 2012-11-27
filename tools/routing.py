#!/usr/bin/env python
# Copyright (c) 2012 maidsafe.net limited
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#     * Neither the name of the maidsafe.net limited nor the names of its
#     contributors may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import datetime
import subprocess
import utils
import random
from subprocess import Popen, PIPE, STDOUT
from time import sleep

num_of_nodes = 20
num_of_bootstraps = 2
num_of_vaults = num_of_nodes / 2 - num_of_bootstraps
num_of_clients = num_of_nodes - num_of_vaults - num_of_bootstraps


def SetupKeys(num):
  print("Setting up keys ... ")
  return subprocess.call(['./routing_key_helper', '-c', '-p', '-n', str(num)], stdout=PIPE)


def SearchKeyWordLine(process, keyword, timeout):
  next_line = process.stdout.readline()
  while next_line.find(keyword) == -1:
    next_line = process.stdout.readline()
#    print 'process\t' + next_line.rstrip()
  return next_line


def ExtractNodeEndpoint(p_b):
  peer_line = SearchKeyWordLine(p_b, 'Current BootStrap node endpoint info', 3)
  if peer_line == -1:
    return -1
  peer = peer_line.split()[7]
  return peer


def ParseSecondsFromString(duration):
  times = duration.split(':')
  hour = float(times[0])
  minute = float(times[1])
  second = float(times[2])
  return hour * 3600 + minute * 60 + second


def SetupBootstraps():
  p_b0 = Popen('./routing_node -s -b -i 0', shell = True, stdout=PIPE, stdin=PIPE)
  p_b1 = Popen('./routing_node -s -b -i 1', shell = True, stdout=PIPE, stdin=PIPE)

  peer_0 = ExtractNodeEndpoint(p_b0)
  if peer_0 == -1:
    KillBootstraps(p_b0, p_b1)
    return -1

  peer_1 = ExtractNodeEndpoint(p_b1)
  if peer_1 == -1:
    KillBootstraps(p_b0, p_b1)
    return -1
  sleep(1)

  p_b0.stdin.write('peer ' + peer_1 + '\n')
  p_b1.stdin.write('peer ' + peer_0 + '\n')

  p_b0.stdin.write('zerostatejoin\n')
  p_b1.stdin.write('zerostatejoin\n')
  sleep(1)
  print("Setup boostrap nodes ...")
  return [peer_0, p_b0, p_b1]


def AddRoutingObject(peer, idx):
  if idx < (num_of_nodes / 2):
    p_v = Popen('./routing_node -s -i ' + str(idx) + ' -p ' + peer, shell = True, stdout=PIPE, stdin=PIPE)
  if idx >= (num_of_nodes / 2):
    p_v = Popen('./routing_node -s -c -i ' + str(idx) + ' -p ' + peer, shell = True, stdout=PIPE, stdin=PIPE)

  key_line = SearchKeyWordLine(p_v, 'Current Node joined', 3)
  if key_line == -1:
    return -1;
  return p_v


def SetupRoutingNodes(peer, num_vaults, num_clients):
  print("Setup " + str(num_vaults) + " vaults and " + str(num_clients) + " clients, please wait ....")
  p_nodes = range(num_vaults + num_clients)
  i = 0;
  while i < (num_vaults + num_clients):
    if i < num_vaults:
      p_nodes[i] = AddRoutingObject(peer, i + num_of_bootstraps)
    if i >= num_vaults:
      p_nodes[i] = AddRoutingObject(peer, (num_of_nodes / 2) + (i - num_vaults))
    if p_nodes[i] == -1:
      print 'Failed to add routing object ' + str(i + num_of_bootstraps) + ' !'
      #TODO cleanup the previous opened nodes
      return -1
    i = i + 1
    sleep(1)
  return p_nodes


def StopNodes(p_nodes):
  for p_node in p_nodes:
    p_node.stdin.write('exit' + '\n')
  sleep(1)
  if p_node.poll() == None:
    print "Failed to stop a node!"
  return 0    


def CheckClientNodeIsNotInRoutingTable(p_c, to_index):
  for index in range(0, to_index):
    p_c.stdin.write('rrt ' + str(index) + '\n')
    sleep(1)
  p_c.stdin.write('help\n')
  node_id = ''
  count = 0
  stop = False
  while stop == False:
    next_line = p_c.stdout.readline()
    if next_line.find('Sending a msg from ') != -1:
      node_id = ((next_line.split(':')[1]).split(' ')[1])
 #     print 'node_id ' + node_id
      count = count -1
    if node_id != '':
      if next_line.find(node_id) != -1:
        count = count + 1
    if next_line.find('exit Exit application.') != -1:
      stop = True
  return count

def SendGroup(p, target):
#  print 'Send group message to ' + str(target)
  p.stdin.write('sendgroup ' + str(target) + '\n')
  sleep(1)
  p.stdin.write('help\n')
  stop = False
  while stop == False:
    next_line = p.stdout.readline()
    if next_line.find('Failure') != -1:
      return -1
    if next_line.find('exit Exit application.') != -1:
      stop = True
  return 0


def JAV1(peer):
  print("Running Routing Sanity Check JAV1 Test, please wait ....")
  p_v = AddRoutingObject(peer, 2)
  if p_v == -1:
    print 'Failed to add routing object!'
    return -1
  p_v.stdin.write('exit' + '\n')
  sleep(2)
  if p_v.poll() == None:
    print "Failed to stop node 2!"
    return -1
  return 0


def JAV2(peer):
  print("Running Routing Sanity Check JAV2 Test, please wait ....")
  p_v = AddRoutingObject(peer, 8)
  if p_v == -1:
    print 'Failed to add routing object!'
    return -1
  #TODO - self-message
  p_v.stdin.write('exit' + '\n')
  sleep(2)
  if p_v.poll() == None:
    print "Failed to stop node 2!"
    return -1
  return 0


def SendDirectMsg(p_nodes, src, dst, datasize):
  print("\tSending a " + str(datasize) + " Bytes msg from " + str(src) + " to " + str(dst) + ", please wait ...")
  p_nodes[src].stdin.write('datasize ' + str(datasize) + '\n')
  p_nodes[src].stdin.write('senddirect ' + str(dst) + '\n')
  key_line = SearchKeyWordLine(p_nodes[src], 'Response received in', 10)
  if key_line == -1:
    print("Failed in sending a msg from " + str(src) + " to " + str(dst))
    return -1;
  duration = key_line.split()[3]
  print("\t"+ str(datasize) + " Bytes data exchanged in " + duration + " seconds")
  return ParseSecondsFromString(duration)


def P1(peer, p_nodes):
  if p_nodes == -1:
    return -1;
  print("Running Routing Sanity Check P1 Test, please wait ....")
  duration = 0
  num_iteration = 5
  for i in range(num_iteration): # vault to vault
    source = random.randint(0, num_of_nodes / 2 - 1)
    dest = random.randint(0, num_of_nodes / 2 - 1) # dest can be a bootstrap node
    if dest != source: # send to self will be super quick, shall be excluded
      result = SendDirectMsg(p_nodes, source, dest, 1048576)
      if result == -1:
        return -1
      duration = duration + result
    else:
      i = i - 1
  print('\tAverage transmission time of 1 MB data from vault to vault is : ' + str(duration / num_iteration))

  duration = 0
  for i in range(num_iteration): # client to vault
    source = random.randint(num_of_nodes / 2, num_of_nodes - 1)
    dest = random.randint(0, num_of_nodes / 2 - 1) # dest can be a bootstrap node
    result = SendDirectMsg(p_nodes, source, dest, 1048576)
    if result == -1:
      return -1
    duration = duration + result
  print('\tAverage transmission time of 1 MB data from client to vault is : ' + str(duration / num_iteration))
  return 0


def JAC1():
  print 'Tesing JAC1'
  if not SetupKeys(20) == 0:
    return -1
  items = SetupBootstraps()
  if items == -1:
    return -1
  peer = items[0]
  p_b0 = items[1]
  p_b1 = items[2]

  p_vs = AddRoutingObjects(peer, 2, 6, '')
  if p_vs == -1:
    print 'At lease one node among 6 nodes failed to start'
    StopBootstrap(p_b0, p_b1)
    return -1

  p_c = AddTypedRoutingObject(peer, 11, 'Client')
  if p_c == -1:
    print 'Failed to start client node'
    StopBootstraps(p_b0, p_b1)
    StopRoutingNodes(p_vs)
    return -1
  p_vs.append(p_c)

  if SendToDirect(p_c, 11) != -1:
#    print 'Client failed to send to self'
    StopBootstraps(p_b0, p_b1)
    StopRoutingObjects(p_vs)
    return -1

  if SendToDirect(p_c, 5) == -1:
    print 'Client failed to send to vault'
    StopBootstraps(p_b0, p_b1)
    StopRoutingObjects(p_vs)
    return -1

  if CheckClientNodeIsNotInRoutingTable(p_c, 6) != 0:
    StopBootstraps(p_b0, p_b1)
    StopRoutingObjects(p_vs)
    return -1

  print ''
  print 'Removing nodes ...'
  StopBootstraps(p_b0, p_b1)
  StopRoutingObjects(p_vs)
  print 'PASSED'
  return 0

def JAC2():
  print 'Testing JAC2'
  if not SetupKeys(20) == 0:
    return -1
  items = SetupBootstraps()
  if items == -1:
    return -1
  peer = items[0]
  p_b0 = items[1]
  p_b1 = items[2]

  p_vs = AddRoutingObjects(peer, 2, 6, '')
  if p_vs == -1:
    print 'At lease one node among 6 nodes failed to start'
    StopBootstrap(p_b0, p_b1)
    return -1

  p_cs = AddRoutingObjects(peer, 11, 6, 'Client')
  if p_cs == -1:
    print 'At lease one node among 6 nodes failed to start'
    StopBootstraps(p_b0, p_b1)
    StopRoutingNodes(p_vs)
    return -1
  p_vs = p_vs + p_cs

  p_v = AddTypedRoutingObject(peer, 8, '')
  if p_v == -1:
    print 'Failed to join the network'
    StopBootstraps(p_b0, p_b1)
    StopRoutingObjects(p_vs)
    return -1

  p_vs.append(p_v)
  print 'Validate routing table',
  for p_c in p_cs:
    print '...',
    if CheckClientNodeIsNotInRoutingTable(p_c, 8) != 0:
      print "Routing tables are not valid"
      StopBootstraps(p_b0, p_b1)
      StopRoutingObjects(p_vs)
      return -1
  print ''
  print 'Removing nodes ...'
  StopBootstraps(p_b0, p_b1)
  StopRoutingObjects(p_vs)
  print 'PASSED'
  return 0

def  SGM1():
  print 'Testing SGM1'
  if not SetupKeys(20) == 0:
    return -1
  items = SetupBootstraps()
  if items == -1:
    return -1
  peer = items[0]
  p_b0 = items[1]
  p_b1 = items[2]

  p_vs = items[1:3]
  p_vs = p_vs + AddRoutingObjects(peer, 2, 6, '')
  if p_vs == -1:
    print 'At lease one node among 6 nodes failed to start'
    StopRoutingObjects(p_vs)
    return -1

  p_cs = AddRoutingObjects(peer, 11, 6, 'Client')
  if p_cs == -1:
    print 'At lease one node among 6 nodes failed to start'
#    StopBootstraps(p_b0, p_b1)
    StopRoutingObjects(p_vs)
    return -1
  p_vs = p_vs + p_cs

  print 'Send group messages to self [',
  for i in range(1, 20):
    rnd = random.randint(0, 13)
    target = rnd;
    if rnd > 7:
      target = rnd + 3
#    print 'rnd, dest: ' + str(rnd) + ', ' + str(target)
    print str(target),
    if SendGroup(p_vs[rnd], target) != 0:
      print "Failed to send group message"
#      StopBootstraps(p_b0, p_b1)
      StopRoutingNodes(p_vs)
      return -1
  print ']'

  print 'Send group messages to random destinations from [',
  for i in range(1, 20):
    rnd = random.randint(0, 13)
    target = random.randint(0, 19)
    if rnd > 7:
      print str(rnd + 3),
    else:
      print str(rnd),
    if SendGroup(p_vs[rnd], target) != 0:
      print "Failed to send group message"
#      StopBootstraps(p_b0, p_b1)
      StopRoutingNodes(p_vs)
      return -1
  print ']'

  StopRoutingObjects(p_vs)
  return 0


def SanityCheck():
  print("Running Routing Sanity Check, please wait ....")

  if not SetupKeys(num_of_nodes) == 0:
    return -1
  items = SetupBootstraps()
  if items == -1:
    return -1
  peer = items[0]
  p_bs = [items[1], items[2]]

  if JAV1(peer) == 0:
    print 'Routing Sanity Check  Test JAV1  : PASSED\n'
  else:
    print 'Routing Sanity Check  Test JAV1  : FAILED\n'

  if JAV2(peer) == 0:
    print 'Routing Sanity Check  Test JAV2  : PASSED\n'
  else:
    print 'Routing Sanity Check  Test JAV2  : FAILED\n'

  p_new_nodes = SetupRoutingNodes(peer, num_of_vaults, num_of_clients)
  p_nodes = p_bs + p_new_nodes

  if P1(peer, p_nodes) == 0:
    print 'Routing Sanity Check  Test P1  : PASSED\n'
  else:
    print 'Routing Sanity Check  Test P1  : FAILED\n'

  StopNodes(p_nodes)


def main():
  print("This is the suite for lifestuff Qa analysis")
  SanityCheck()

if __name__ == "__main__":
  sys.exit(main())

