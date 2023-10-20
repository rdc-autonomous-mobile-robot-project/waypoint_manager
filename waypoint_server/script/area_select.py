#!/usr/bin/env python3

from geometry_msgs.msg import Twist
from std_msgs.msg import UInt8
from std_msgs.msg import String
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, SetBoolResponse
from std_srvs.srv import Trigger, TriggerResponse
import rospy


class AreaSelectNode():
    def __init__(self):
        rospy.init_node('area_select', anonymous=True)
        self.time = 0
        self.detect_box_flag =False
        self.area_select_sucess = False
        self.area_select_flag = False
        self.select_exec = False
        self.area = ""
        self.area_skip_seq = ""
        self.A_waypoint = rospy.get_param("/area_select/bigining_area_A", 6)
        self.B_waypoint = rospy.get_param("/area_select/bigining_area_B", 3)
        self.C_waypoint = rospy.get_param("/area_select/bigining_area_C", 1)
        self.skip_waypoint_num = rospy.Publisher("/waypoint_manager/waypoint_next_num", UInt8, queue_size=10)
        self.tag_sub = rospy.Subscriber("/label_string", String, self.label_getter_cb)
        self.detect_box = rospy.Service('/detect_box', SetBool, self.detect_box_server)
        self.area_point = rospy.Service('/area_waypoint', SetBool, self.area_point_server)
        self.result_sv = rospy.Service('/detect_result', SetBool, self.detect_result_server)
        self.area_select_sv = rospy.Service('/area_select', SetBool, self.area_select_server)
        self.skip_waypoint= rospy.ServiceProxy('/waypoint_manager/waypoint_server/next_waypoint', Trigger)




    def label_getter_cb(self, area_str):
        if self.select_exec:
            self.area = area_str.data
            rospy.loginfo("get area label %s" % self.area)
        else:
            rospy.logwarn_once("NOT EXECUTED select task yet")


    def detect_box_server(self, request):
        if self.select_exec:
            if request.data:
                self.detect_box_flag = True
                rospy.loginfo("start box detect")

                rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
                try:
                    self.skip_waypoint()
                except rospy.ServiceException as err:
                    rospy.logfatal("Service call failed: %s" %err)

                return SetBoolResponse (True, 'start detect box')
            else:
                self.detect_box_flag = False
                rospy.logwarn("not start box detect")
                return SetBoolResponse(False, 'not start detect box')
        else:
            rospy.logwarn("NOT EXECUTED select task yet")
            return SetBoolResponse(False, 'NOT EXECUTE')
        
    
    def area_point_server(self, request):
        if request.data:
            self.select_exec = True
            rospy.loginfo("start delivery area")
            return SetBoolResponse (True, 'start delivery area')
        else:
            self.select_exec = False
            rospy.logwarn("end delivery area")
            return SetBoolResponse(False, 'end delivery area')


    def area_select_server(self, request):
        if self.select_exec and request.data:
            if self.area_select_flag:
                rospy.loginfo("getting area tag...")
                self.area_skip_seq = self.area_selector()
                if self.area_skip_seq == "a" or "b" or "c":
                    rospy.loginfo("area selected!")
                    self.area_select_flag = False
                else:
                    rospy.logwarn("box not detected")
                    self.return_nav_point_skip()
                    self.area_select_flag = False
            else:
                rospy.logwarn("box not detected")
                self.return_nav_point_skip()
                self.area_select_flag = False
        else:
            rospy.logwarn("NOT EXECUTED select task yet")
            return SetBoolResponse(False, 'NOT EXECUTE')
    

    def detect_result_server(self, request):
        if self.select_exec:
            if request.data:
                self.area_select_flag = True
                rospy.loginfo("start selecting area")
                return SetBoolResponse (True, 'detect success')
            else:
                rospy.logwarn("start selecting area")
                return SetBoolResponse(False, 'detect failed')
        else:
            rospy.logwarn("NOT EXECUTED select task yet")
            return SetBoolResponse(False, 'NOT EXECUTE')
        

    def area_selector(self):
        if self.area == 'tag_a':
            rospy.loginfo("select area A")
            self.skip_waypoint_num.publish(self.C_waypoint + self.B_waypoint)

            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)

            self.area = ""
            return "a"

        elif self.area == 'tag_b':
            rospy.loginfo("select area B")
            self.skip_waypoint_num.publish(self.C_waypoint)

            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)
            
            self.area = ""
            return "b"
            
        elif self.area == 'tag_c':
            rospy.loginfo("select area C")
            return "c"
        
        else:
            rospy.loginfo("detected failed")
            self.skip_waypoint_num.publish(self.C_waypoint + self.B_waypoint)

            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)
            return "failed"


    def return_nav_point_skip(self):
        rospy.loginfo("waypoint skipping")
        if self.area_skip_seq == 'a':
            rospy.loginfo("return navigation at area A")
            return 

        elif self.area_skip_seq == 'b':
            rospy.loginfo("return navigation at area B")
            self.skip_waypoint_num.publish(self.A_waypoint)
        
            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)
            
            self.skip_area()
            return 

        elif self.area_skip_seq == 'c':
            rospy.loginfo("return navigation at area C")
            self.skip_waypoint_num.publish(self.B_waypoint)

            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)

            self.skip_area()
            return 

        else:
            rospy.loginfo("return navigation with detection failed")
            self.skip_waypoint_num.publish(self.C_waypoint + self.B_waypoint)

            rospy.wait_for_service('waypoint_manager/waypoint_server/next_waypoint')
            try:
                self.skip_waypoint()
            except rospy.ServiceException as err:
                rospy.logfatal("Service call failed: %s" %err)
            self.skip_area()
            return 


    def loop(self):
        if self.select_exec:
            rospy.loginfo_once("---- area select process execute ----")
            if self.time % 5 == 0:
                rospy.loginfo("job progress")
        self.time += DURATION

                


if __name__ == '__main__':
    rospy.loginfo("area select started")
    node = AreaSelectNode()
    DURATION = 1
    r = rospy.Rate(1 / DURATION)
    while not rospy.is_shutdown():
        node.loop()
        r.sleep()