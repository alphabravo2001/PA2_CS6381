###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the discovery middleware code
#
# Created: Spring 2023
#
###############################################

# Designing the logic is left as an exercise for the student.
#
# The discovery service is a server. So at the middleware level, we will maintain
# a REP socket binding it to the port on which we expect to receive requests.
#
# There will be a forever event loop waiting for requests. Each request will be parsed
# and the application logic asked to handle the request. To that end, an upcall will need
# to be made to the application logic.

import zmq  # ZMQ sockets
import json

# import serialization logic
from CS6381_MW import discovery_pb2


class DiscoveryMW():

    ########################################
    # constructor
    ########################################
    def __init__(self, logger):
        self.logger = logger  # internal logger for print statements
        self.rep = None  # will be a ZMQ REP socket
        self.poller = None  # used to wait on incoming replies
        self.addr = None  # our advertised IP address
        self.port = None  # port num where we are going to publish our topics
        self.upcall_obj = None  # handle to appln obj to handle appln-specific data
        self.handle_events = True  # in general we keep going thru the event loop
        self.name = None
        self.hashval = None
        self.disclookup = {}

        self.reqdict = {}   # dictionary of the req circuits
        self.req = None

        self.filename = "fingertable.json"
        self.hmfinger = {}
        self.hasharr = []

        self.hashval = None
        self.arr = []

        self.l = None



    def configure(self, args):
        ''' Initialize the object '''

        try:
            # Here we initialize any internal variables
            self.logger.info("DiscoveryMW::configure")

            # First retrieve our advertised IP addr and the publication port num
            self.port = args.port
            self.addr = "10.0.0.1:5555"
            self.name = args.name
            self.l = args.iflocal

            # Next get the ZMQ context
            self.logger.debug("DiscoveryMW::configure - obtain ZMQ context")
            context = zmq.Context()  # returns a singleton object

            # get the ZMQ poller object
            self.logger.debug("DiscoveryMW::configure - obtain the poller")
            self.poller = zmq.Poller()

            # Now acquire the REP sockets
            self.logger.info("DiscoveryMW::configure - obtain REP socket")
            self.rep = context.socket(zmq.REP)


            # Since are using the event loop approach, register the REQ socket for incoming events
            # Note that nothing ever will be received on the PUB socket and so it does not make
            # any sense to register it with the poller for an incoming message.
            self.logger.debug("DiscoveryMW::configure - register the REQ socket for incoming replies")
            self.poller.register(self.rep, zmq.POLLIN)

            f_ = open("dht.json")
            temp = json.loads(f_.read())["dht"]

            #store fingertable
            f = open(self.filename)
            self.hmfinger = json.loads(f.read())

            for arr in temp:
                if arr["id"] == self.name:
                    self.hashval = arr["hash"]

                    addr = arr["IP"]
                    port = arr["port"]

                    if self.l:
                        bind_string = "tcp://*:" + str(port)
                        print ("cur ", bind_string)
                    else:
                        bind_string = "tcp://{}:{}".format(addr, port)

                    self.rep.bind(bind_string)

                self.disclookup[arr["hash"]] = (arr["id"], arr["port"], arr["IP"], arr["host"])


            for arr in temp:
                if arr["hash"] not in self.reqdict:
                    self.reqdict[arr["hash"]] = context.socket(zmq.REQ)
                    self.poller.register(self.reqdict[arr["hash"]], zmq.POLLIN)
                    name = arr["id"]

                    addr = arr["IP"]
                    port = arr["port"]

                    if self.l:
                        bind_string = "tcp://" + "localhost:" + str(port)
                        #bind_string = "tcp://*:" + str(port)
                    else:
                        bind_string = "tcp://{}:{}".format(addr, port)

                    self.reqdict[arr["hash"]].connect(bind_string)


            self.logger.info("DiscoveryMW::configure completed")

        except Exception as e:
            raise e


    def event_loop(self, timeout=None):

        try:
            self.logger.info("DiscoveryMW::event_loop - run the event loop")

            # we are using a class variable called "handle_events" which is set to
            # True but can be set out of band to False in order to exit this forever
            # loop

            while self.handle_events:  # it starts with a True value
                # poll for events. We give it an infinite timeout.
                # The return value is a socket to event mask mapping
                events = dict(self.poller.poll(timeout=timeout))

                for ev in self.reqdict.values():
                    if ev in events:
                        timeout = self.handle_response_back(ev)

                if self.rep in events:
                    timeout = self.handle_request()


            self.logger.info("DiscoveryMW::event_loop - out of the event loop")

        except Exception as e:
            raise e



    #################################################################
    # handle an incoming response
    ##################################################################
    def handle_response_back(self, ev):

        try:
            self.logger.debug("DiscoveryMW::handle_request")

            for key in self.reqdict:
                if self.reqdict[key] == ev:

                    bytesRcvd = self.reqdict[key].recv()

                    # now use protobuf to deserialize the bytes
                    disc_resp = discovery_pb2.DiscoveryResp()
                    disc_resp.ParseFromString(bytesRcvd)

                    if (disc_resp.msg_type == discovery_pb2.TYPE_REGISTER_CHORD_RESP):
                        timeout = self.upcall_obj.register_request_chord_resp(disc_resp.chord_register_resp)

                    elif (disc_resp.msg_type == discovery_pb2.TYPE_CHORD_LOOKUP_RESP):
                        timeout = self.upcall_obj.lookup_request_chord_resp(disc_resp.chord_lookup_resp)

        except Exception as e:
            raise e


    #################################################################
    # handle an incoming reply
    ##################################################################
    def handle_request(self):

        try:
                self.logger.info("DiscoveryMW::handle_request")

                # let us first receive all the bytes
                bytesRcvd = self.rep.recv()

                # now use protobuf to deserialize the bytes
                disc_resp = discovery_pb2.DiscoveryReq()
                disc_resp.ParseFromString(bytesRcvd)


                # depending on the message type, the remaining
                # contents of the msg will differ

                # TO-DO
                # When your proto file is modified, some of this here
                # will get modified.
                if (disc_resp.msg_type == discovery_pb2.TYPE_REGISTER):
                    # this is a response to register message
                    timeout = self.upcall_obj.register_request_initial(disc_resp.register_req)

                elif (disc_resp.msg_type == discovery_pb2.TYPE_ISREADY):
                    # this is a response to is ready request
                    timeout = self.upcall_obj.isready_response(disc_resp.isready_req)

                elif (disc_resp.msg_type == discovery_pb2.TYPE_LOOKUP_ALL_PUBS):
                    timeout = self.upcall_obj.pubslookup_response(disc_resp.isready_req)

                elif (disc_resp.msg_type == discovery_pb2.TYPE_LOOKUP_PUB_BY_TOPIC):
                    timeout = self.upcall_obj.lookup_response_initial(disc_resp.lookup_req)

                elif (disc_resp.msg_type == discovery_pb2.TYPE_CHORD_REGISTER):
                    timeout = self.upcall_obj.register_request_chord(disc_resp.chord_req)

                elif (disc_resp.msg_type == discovery_pb2.TYPE_CHORD_LOOKUP):
                    timeout = self.upcall_obj.lookup_request_chord(disc_resp.chord_lookup)


                else:  # anything else is unrecognizable by this object
                    # raise an exception here
                    raise Exception("Unrecognized response message")

        except Exception as e:
            raise e


    #################################################################
    # handle an outgoing response
    ##################################################################
    def handle_response(self, resp):
        buf2send = resp.SerializeToString()
        self.logger.info("Stringified serialized buf = {}".format(buf2send))
        self.rep.send(buf2send)  # we use the "send" method of ZMQ that sends the bytes


    #################################################################
    # handle an outgoing chord request
    ##################################################################
    def handle_chord_req(self, req, hash):
        buf2send = req.SerializeToString()
        self.logger.info("Chord req: Stringified serialized buf = {}".format(buf2send))
        self.reqdict[hash].send(buf2send) # we use the "send" method of ZMQ that sends the bytes


    ########################################
    # set upcall handle
    #
    # here we save a pointer (handle) to the application object
    ########################################
    def set_upcall_handle(self, upcall_obj):
        ''' set upcall handle '''
        self.upcall_obj = upcall_obj


    ########################################
    # disable event loop
    #
    # here we just make the variable go false so that when the event loop
    # is running, the while condition will fail and the event loop will terminate.
    ########################################
    def disable_event_loop(self):
        ''' disable event loop '''
        self.handle_events = False
