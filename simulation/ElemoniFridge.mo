model ElemoniFridge "Uncalibrated thermal fridge with RMS electrical envelope"
  parameter Modelica.Units.SI.HeatCapacity C=20000;
  parameter Modelica.Units.SI.ThermalConductance G=2;
  parameter Modelica.Units.SI.Temperature Tamb=303.15;
  parameter Modelica.Units.SI.Temperature Tinitial=278.15;
  parameter Modelica.Units.SI.Temperature Tlow=276.15;
  parameter Modelica.Units.SI.Temperature Thigh=278.15;
  parameter Modelica.Units.SI.Power Prun=120;
  parameter Real COP=1.5 "Constant illustrative cooling coefficient";
  parameter Modelica.Units.SI.Power Pstandby=2;
  parameter Modelica.Units.SI.Power Pbackground=100;
  parameter Modelica.Units.SI.Power Pstart=480 "Extra startup active power";
  parameter Modelica.Units.SI.Time startDuration=2;
  parameter Real powerFactor=0.8;
  parameter Modelica.Units.SI.Voltage Vrms=220;
  parameter Modelica.Units.SI.Frequency f=50 "Supply metadata; no AC waveform solved";
  parameter Boolean doorEnabled=true;
  parameter Modelica.Units.SI.Power Pdoor=150;
  // Guards allow the explicit configuration assertion to report invalid inputs
  // before a generated algebraic division fails during initialization.
  Modelica.Thermal.HeatTransfer.Components.HeatCapacitor cabinet(C=max(C,1e-9), T(start=Tinitial, fixed=true))
    annotation(Placement(transformation(origin={0,20},extent={{-10,-10},{10,10}})));
  Modelica.Thermal.HeatTransfer.Components.ThermalConductor wall(G=G)
    annotation(Placement(transformation(origin={-40,0},extent={{-10,-10},{10,10}})));
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature ambient(T=Tamb)
    annotation(Placement(transformation(origin={-80,0},extent={{-10,-10},{10,10}})));
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow coolingAndDoor
    annotation(Placement(transformation(origin={40,0},extent={{-10,-10},{10,10}},rotation=180)));
  output Real cabinetC(unit="degC");
  output Boolean compressorOn;
  output Boolean doorOpen;
  output Modelica.Units.SI.Power pStartup;
  output Modelica.Units.SI.Power pFridge "Cycle-mean active power envelope";
  output Modelica.Units.SI.Power pTotal;
  output Modelica.Units.SI.ReactivePower qReactive;
  output Modelica.Units.SI.Current iRms;
  output Real energyWh(unit="W.h", start=0, fixed=true);
  output Modelica.Units.SI.HeatFlowRate qWall;
  output Modelica.Units.SI.HeatFlowRate qDoor;
  output Modelica.Units.SI.HeatFlowRate qCooling;
  output Modelica.Units.SI.TemperatureSlope thermalSlope;
protected
  discrete Modelica.Units.SI.Time lastStart(start=-1e9, fixed=true);
initial equation
  assert(C > 0 and G > 0 and Prun > 0 and COP > 0 and Vrms > 0 and f > 0
    and startDuration > 0 and Pstandby >= 0 and Pbackground >= 0 and Pstart >= 0
    and Pdoor >= 0 and powerFactor > 0 and powerFactor <= 1
    and Tlow > 0 and Tlow < Thigh and Tamb > 0 and Tinitial > 0,
    "Invalid refrigerator configuration");
equation
  connect(ambient.port, wall.port_a) annotation(Line(points={{-70,0},{-50,0}},color={191,0,0}));
  connect(wall.port_b, cabinet.port) annotation(Line(points={{-30,0},{0,0},{0,10}},color={191,0,0}));
  connect(coolingAndDoor.port, cabinet.port) annotation(Line(points={{30,0},{0,0},{0,10}},color={191,0,0}));
  when initial() then
    compressorOn = Tinitial >= Thigh;
  elsewhen cabinet.T >= Thigh then
    compressorOn = true;
  elsewhen cabinet.T <= Tlow then
    compressorOn = false;
  end when;
  when initial() then
    lastStart = if Tinitial >= Thigh then time else -1e9;
  elsewhen compressorOn then
    lastStart = time;
  end when;
  doorOpen = doorEnabled and mod(time,7200) >= 3600 and mod(time,7200) < 3660;
  qDoor = if doorOpen then Pdoor else 0;
  qWall = G*(Tamb-cabinet.T);
  qCooling = if compressorOn then COP*Prun else 0;
  coolingAndDoor.Q_flow = qDoor-qCooling;
  cabinetC = cabinet.T-273.15;
  thermalSlope = der(cabinet.T);
  pStartup = if compressorOn and time < lastStart+startDuration then Pstart else 0;
  pFridge = Pstandby + (if compressorOn then Prun else 0) + pStartup;
  pTotal = Pbackground + pFridge;
  qReactive = ((if compressorOn then Prun else 0)+pStartup)*sqrt(max(0,1/max(powerFactor,1e-9)^2-1));
  iRms = sqrt(pTotal^2+qReactive^2)/max(Vrms,1e-9);
  der(energyWh) = pFridge/3600;
  annotation(uses(Modelica(version="4.1.0")),
    experiment(StartTime=0,StopTime=21600,Interval=1,Tolerance=1e-7),
    Documentation(info="<html><p>Synthetic lumped thermal refrigerator. RMS electrical envelope only; not a motor or refrigerant model. Parameters are assumptions, not calibrated appliance data.</p></html>"));
end ElemoniFridge;
