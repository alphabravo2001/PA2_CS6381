###############################################
#
# Author: Aniruddha Gokhale
# Vanderbilt University
#
# Purpose: Skeleton/Starter code for the Discovery application
#
# Created: Spring 2023
#
###############################################


# This is left as an exercise for the student.  The Discovery service is a server
# and hence only responds to requests. It should be able to handle the register,
# is_ready, the different variants of the lookup methods. etc.
#
# The key steps for the discovery application are
# (1) parse command line and configure application level parameters. One
# of the parameters should be the total number of publishers and subscribers
# in the system.
# (2) obtain the discovery middleware object and configure it.
# (3) since we are a server, we always handle events in an infinite event loop.
# See publisher code to see how the event loop is written. Accordingly, when a
# message arrives, the middleware object parses the message and determines
# what method was invoked and then hands it to the application logic to handle it
# (4) Some data structure or in-memory database etc will need to be used to save
# the registrations.
# (5) When all the publishers and subscribers in the system have registered with us,
# then we are in a ready state and will respond with a true to is_ready method. Until then
# it will be false.

import os  # for OS functions
import sys  # for syspath and system exception
import time  # for sleep
import argparse  # for argument parsing
import configparser  # for configuration parsing
import logging  # for logging. Use it in place of print statements.

# Import our topic selector. Feel free to use alternate way to
# get your topics of interest
from topic_selector import TopicSelector

# Now import our CS6381 Middleware
from CS6381_MW.DiscoveryMW import DiscoveryMW
# We also need the message formats to handle incoming responses.
from CS6381_MW import discovery_pb2

# import any other packages you need.
from enum import Enum  # for an enumeration we are using to describe what state we are in



class DiscoveryAppln():

    def __init__(self, logger):
        self.pubs = None
        self.subs = None
        self.mw_obj = None  # handle to the underlying Middleware object
        self.logger = logger  # internal logger for print statements
        self.lookup = None
        self.dissemination = None
        self.hm = {}  #for pubs
        self.hm2 = {} #for subs
        self.cur_pubs = 0
        self.cur_subs = 0
        self.pubset = set()

        self.broker_addr = None
        self.broker_port = None

    def configure(self, args):
        ''' Initialize the object '''

        try:
            # Here we initialize any internal variables
            self.logger.info("DiscoveryAppln::configure")

            # initialize our variables
            self.subs = args.subs
            self.pubs = args.pubs

            # Now, get the configuration object
            self.logger.debug("DiscoveryAppln::configure - parsing config.ini")
            config = configparser.ConfigParser()
            config.read(args.config)
            self.lookup = config["Discovery"]["Strategy"]
            self.dissemination = config["Dissemination"]["Strategy"]

            # Now setup up our underlying middleware object to which we delegate
            # everything
            self.logger.debug("DiscoveryAppln::configure - initialize the middleware object")
            self.mw_obj = DiscoveryMW(self.logger)
            self.mw_obj.configure(args)  # pass remainder of the args to the m/w object

            self.logger.info("DiscoveryAppln::configure - configuration complete")

        except Exception as e:
            raise e


    ########################################
    # driver program
    # ########################################
    def driver(self):
        ''' Driver program '''

        try:
            self.logger.info("DiscoveryAppln::driver")

            # dump our contents (debugging purposes)
            #self.dump()

            # First ask our middleware to keep a handle to us to make upcalls.
            # This is related to upcalls. By passing a pointer to ourselves, the
            # middleware will keep track of it and any time something must
            # be handled by the application level, invoke an upcall.
            self.logger.debug("DiscoveryAppln::driver - upcall handle")
            self.mw_obj.set_upcall_handle(self)

            # Now simply let the underlying middleware object enter the event loop
            # to handle events. However, a trick we play here is that we provide a timeout
            # of zero so that control is immediately sent back to us where we can then
            # register with the discovery service and then pass control back to the event loop
            #
            # As a rule, whenever we expect a reply from remote entity, we set timeout to
            # None or some large value, but if we want to send a request ourselves right away,
            # we set timeout is zero.
            #
            self.mw_obj.event_loop(timeout=0)  # start the event loop

            self.logger.info("DiscoveryAppln::driver completed")

        except Exception as e:
            raise e



    def register_request(self, register_req):
        # TOPICS 2 PUBs
        # PUBS : SET( (ip, port) )

        self.logger.info("DiscoveryAppln::register request started")

        try:

            if register_req.role == discovery_pb2.ROLE_PUBLISHER:

                for topic in register_req.topiclist:

                    if topic not in self.hm:
                        self.hm[topic] = [(register_req.info.id,register_req.info.addr,register_req.info.port)]
                    else:
                        self.hm[topic].append((register_req.info.id,register_req.info.addr,register_req.info.port))


                    if (register_req.info.id,register_req.info.addr,register_req.info.port) not in self.pubset:
                        self.pubset.add((register_req.info.id,register_req.info.addr,register_req.info.port))


                ready_resp = discovery_pb2.RegisterResp()
                ready_resp.status = discovery_pb2.STATUS_SUCCESS

                self.mw_obj.handle_response(ready_resp)

                self.cur_pubs += 1

                print (self.hm)


            elif register_req.role == discovery_pb2.ROLE_SUBSCRIBER:

                for topic in register_req.topiclist:
                    if topic not in self.hm2:
                        self.hm2[topic] = [(register_req.info.id, register_req.info.addr,
                                           register_req.info.port)]

                    else:
                        self.hm2[topic].append((register_req.info.id, register_req.info.addr,
                                               register_req.info.port))

                ready_resp = discovery_pb2.RegisterResp()
                ready_resp.status = discovery_pb2.STATUS_SUCCESS

                self.mw_obj.handle_response(ready_resp)

                self.cur_subs += 1


            elif register_req.role == discovery_pb2.ROLE_BOTH:

                self.broker_addr = register_req.info.addr
                self.broker_port = register_req.info.port

                ready_resp = discovery_pb2.RegisterResp()
                ready_resp.status = discovery_pb2.STATUS_SUCCESS

                self.mw_obj.handle_response(ready_resp)


            self.logger.info("DiscoveryAppln::register completed")

        except Exception as e:
            raise e




    def isready_response(self, isready_req):

        self.logger.info("DiscoveryAppln::is ready request started")

        try:
            if self.pubs+self.subs == self.cur_pubs+self.cur_subs:

                if self.dissemination == "Broker":
                    if self.broker_addr and self.broker_port:

                        ready_resp = discovery_pb2.IsReadyResp()
                        ready_resp.status = discovery_pb2.STATUS_SUCCESS

                        discovery_resp = discovery_pb2.DiscoveryResp()
                        discovery_resp.isready_resp.CopyFrom(ready_resp)
                        discovery_resp.msg_type = discovery_pb2.TYPE_ISREADY

                        self.mw_obj.handle_response(discovery_resp)

                        self.logger.info("DiscoveryAppln:: SUCCESS; DISSEMINATION CAN NOW BEGIN")

                    else:
                        ready_resp = discovery_pb2.IsReadyResp()
                        ready_resp.status = discovery_pb2.STATUS_FAILURE

                        discovery_resp = discovery_pb2.DiscoveryResp()
                        discovery_resp.isready_resp.CopyFrom(ready_resp)
                        discovery_resp.msg_type = discovery_pb2.TYPE_ISREADY

                        self.mw_obj.handle_response(discovery_resp)

                        self.logger.info("DiscoveryAppln:: FAILURE; Broker not yet registered")

                else:
                    ready_resp = discovery_pb2.IsReadyResp()
                    ready_resp.status = discovery_pb2.STATUS_SUCCESS

                    discovery_resp = discovery_pb2.DiscoveryResp()
                    discovery_resp.isready_resp.CopyFrom(ready_resp)
                    discovery_resp.msg_type = discovery_pb2.TYPE_ISREADY

                    self.mw_obj.handle_response(discovery_resp)

                    self.logger.info("DiscoveryAppln:: SUCCESS; DISSEMINATION CAN NOW BEGIN")

            else:
                ready_resp = discovery_pb2.IsReadyResp()
                ready_resp.status = discovery_pb2.STATUS_FAILURE

                discovery_resp = discovery_pb2.DiscoveryResp()
                discovery_resp.isready_resp.CopyFrom(ready_resp)
                discovery_resp.msg_type = discovery_pb2.TYPE_ISREADY

                self.mw_obj.handle_response(discovery_resp)

            self.logger.info("DiscoveryAppln::is ready request finished")

        except Exception as e:
            raise e



    def lookup_response(self, lookup_req):

        self.logger.info("DiscoveryAppln::lookup response started")

        try:

            if self.dissemination != "Broker":  #direct

                lookup_resp = discovery_pb2.LookupPubByTopicResp()  # allocate

                for topic in lookup_req.topiclist:
                    if topic in self.hm:
                        for tup in self.hm[topic]:
                            temp = discovery_pb2.RegistrantInfo()

                            id_name = tup[0]
                            add_name = tup[1]
                            port_name = tup[2]

                            temp.id = id_name
                            temp.addr = add_name
                            temp.port = port_name

                            lookup_resp.array.append(temp)


                discovery_resp = discovery_pb2.DiscoveryResp()
                discovery_resp.lookup_resp.CopyFrom(lookup_resp)
                discovery_resp.msg_type = discovery_pb2.TYPE_LOOKUP_PUB_BY_TOPIC

                self.logger.info("DiscoveryAppln::lookup response finished")

                self.mw_obj.handle_response(discovery_resp)


            else:
                # broker - send broker info
                lookup_resp = discovery_pb2.LookupPubByTopicResp()  # allocate
                temp = discovery_pb2.RegistrantInfo()
                temp.id = "Broker"
                temp.addr = self.broker_addr
                temp.port = self.broker_port

                lookup_resp.array.append(temp)

                discovery_resp = discovery_pb2.DiscoveryResp()
                discovery_resp.lookup_resp.CopyFrom(lookup_resp)
                discovery_resp.msg_type = discovery_pb2.TYPE_LOOKUP_PUB_BY_TOPIC

                self.logger.info("DiscoveryAppln::lookup response finished")

                self.mw_obj.handle_response(discovery_resp)



        except Exception as e:
            raise e


    def pubslookup_response(self, pubs_req):

        try:
            self.logger.info("DiscoveryAppln::pubslookup_response response started")
            pubs_resp = discovery_pb2.RegisterPubsResp()

            for tup in self.pubset:

                temp = discovery_pb2.RegistrantInfo()

                id_name = tup[0]
                add_name = tup[1]
                port_name = tup[2]

                temp.id = id_name
                temp.addr = add_name
                temp.port = port_name

                pubs_resp.array.append(temp)

            discovery_resp = discovery_pb2.DiscoveryResp()
            discovery_resp.pubs_resp.CopyFrom(pubs_resp)
            discovery_resp.msg_type = discovery_pb2.TYPE_LOOKUP_ALL_PUBS

            self.logger.info("DiscoveryAppln::pubslookup_response response finished")

            self.mw_obj.handle_response(discovery_resp)

        except Exception as e:
            raise e


def parseCmdLineArgs():
        # instantiate a ArgumentParser object
        parser = argparse.ArgumentParser(description="Discovery Application")

        # Now specify all the optional arguments we support
        # At a minimum, you will need a way to specify the IP and port of the lookup
        # service, the role we are playing, what dissemination approach are we
        # using, what is our endpoint (i.e., port where we are going to bind at the
        # ZMQ level)

        parser.add_argument("-P", "--pubs", type=int, default=1,
                            help="total number of publishers the system")

        parser.add_argument("-S", "--subs", type=int, default=1,
                            help="total number of subscribers the system")

        parser.add_argument("-c", "--config", default="config.ini", help="configuration file (default: config.ini)")

        parser.add_argument("-l", "--loglevel", type=int, default=logging.INFO,
                            choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
                            help="logging level, choices 10,20,30,40,50: default 20=logging.INFO")

        parser.add_argument("-p", "--port", type=int, default=5555,
                            help="Port number on which our underlying publisher ZMQ service runs, default=5555")



        return parser.parse_args()



def main():
    try:
        # obtain a system wide logger and initialize it to debug level to begin with
        logging.info("Main - acquire a child logger and then log messages in the child")
        logger = logging.getLogger("DiscoveryAppln")

        # first parse the arguments
        logger.debug("Main: parse command line arguments")
        args = parseCmdLineArgs()

        # reset the log level to as specified
        logger.debug("Main: resetting log level to {}".format(args.loglevel))
        logger.setLevel(args.loglevel)
        logger.debug("Main: effective log level is {}".format(logger.getEffectiveLevel()))

        # Obtain a publisher application
        logger.debug("Main: obtain the publisher appln object")
        disc_app = DiscoveryAppln(logger)

        # configure the object
        # logger.debug("Main: configure the publisher appln object")
        disc_app.configure(args)

        # now invoke the driver program
        logger.debug("Main: invoke the publisher appln driver")
        disc_app.driver()

    except Exception as e:
        logger.error("Exception caught in main - {}".format(e))
        return



###################################
#
# Main entry point
#
###################################
if __name__ == "__main__":
  # set underlying default logging capabilities
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  main()