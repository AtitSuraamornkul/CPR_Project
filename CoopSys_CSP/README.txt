Copyright (c) 2021  Yoshinao Isobe
National Institute of Advanced Industrial Science and Technology (AIST)
2021/09/27

------------------------------------------------------------------------

         A Formal Model of Cooperative Transport Robots

1. Introduction

This folder includes all the CSPm codes of cooperative transport
robots used for the verification by the model checker FDR4. The detail
of the CSPm codes and the verification is explained in the following
paper:

  Yoshinao Isobe, Nobuhiko Miyamoto, Noriaki Ando, and Yutaka Oiwa,
  Formal Modeling and Verification of Concurrent FSMs: Case Study on
  Event-Based Cooperative Transport Robots, IEICE Transactions on
  Information and Systems, Vol.E104-D, No.10, October 2021.

2. CSPm files

  CoopSys.csp      : Main file
  CoopSys_rev.csp  : Main file (revised)

  CoopSys_spec.csp : The specification of CoopSys
  
  RTM_compo.csp    : The composition of RTCs on RTM
  RTM_spec.csp     : Specification templates

  RoboMng_fsm.csp          : The FSM of the manager of CoopRobo
  RoboMng_fsm_rev.csp      : The FSM of the manager of CoopRobo (revised)
  RoboCtrl_fsm.csp         : The FSM of the controller of CoopRobo
  RaspberryPiMouse_fsm.csp : The FSM of the Raspberry-Pi Mouse
  Client_fsm.csp           : The FSM of the Client

  LICENSE.txt : MIT License

3. How to verify CoopSys

The model checker FDR4 (e.g., ver 4.2.7) is necessary for verifying
CoopSys.csp, and it can be downloaded and installed from the web-site
of FDR4:

  FDR4
  https://cocotec.io/fdr/

Note that FDR is only freely available for academic teaching and
research purposes.

After the installation of FDR4, open "CoopSys.csp" and then
check all the assertions by clicking the button "Run All".

