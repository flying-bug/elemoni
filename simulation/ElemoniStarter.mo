model ElemoniStarter "Synthetic loads; cycling proxy is not a physical fridge"
  parameter Modelica.Units.SI.Voltage Vrms = 220;
  parameter Modelica.Units.SI.Frequency f = 50;
  Modelica.Electrical.Analog.Sources.SineVoltage supply(V=sqrt(2)*Vrms, f=f)
    annotation(Placement(transformation(origin={-70,0}, extent={{-10,-10},{10,10}}, rotation=270)));
  Modelica.Electrical.Analog.Basic.Ground ground
    annotation(Placement(transformation(extent={{-80,-80},{-60,-60}})));
  Modelica.Electrical.Analog.Basic.VariableResistor background
    annotation(Placement(transformation(origin={-30,0}, extent={{-10,-10},{10,10}}, rotation=270)));
  Modelica.Electrical.Analog.Basic.VariableResistor heater
    annotation(Placement(transformation(origin={10,0}, extent={{-10,-10},{10,10}}, rotation=270)));
  Modelica.Electrical.Analog.Basic.VariableResistor cyclingProxy
    annotation(Placement(transformation(origin={50,0}, extent={{-10,-10},{10,10}}, rotation=270)));
  output Modelica.Units.SI.Voltage voltage;
  output Modelica.Units.SI.Current current;
  output Modelica.Units.SI.Power pInstant;
  output Modelica.Units.SI.Power pBase "Analytic cycle mean W";
  output Modelica.Units.SI.Power pHeater "Analytic cycle mean W";
  output Modelica.Units.SI.Power pCycle "Analytic cycle mean W";
  output Modelica.Units.SI.Power pTotal "Analytic cycle mean W";
initial equation
  assert(Vrms > 0 and f > 0, "Supply voltage and frequency must be positive");
equation
  pBase = 100;
  pHeater = if time >= 10 and time < 30 then 1000 else 0;
  pCycle = if mod(time, 20) < 10 then 150 else 0;
  background.R = Vrms^2 / pBase;
  // Off-state electrical leakage < 1e-7 W; analytic labels are exactly zero.
  heater.R = if pHeater > 0 then Vrms^2 / 1000 else 1e15;
  cyclingProxy.R = if pCycle > 0 then Vrms^2 / 150 else 1e15;
  connect(supply.p, background.p) annotation(Line(points={{-70,10},{-70,40},{-30,40},{-30,10}}, color={0,0,255}));
  connect(supply.p, heater.p) annotation(Line(points={{-70,10},{-70,40},{10,40},{10,10}}, color={0,0,255}));
  connect(supply.p, cyclingProxy.p) annotation(Line(points={{-70,10},{-70,40},{50,40},{50,10}}, color={0,0,255}));
  connect(supply.n, ground.p) annotation(Line(points={{-70,-10},{-70,-60}}, color={0,0,255}));
  connect(background.n, ground.p) annotation(Line(points={{-30,-10},{-30,-40},{-70,-40},{-70,-60}}, color={0,0,255}));
  connect(heater.n, ground.p) annotation(Line(points={{10,-10},{10,-40},{-70,-40},{-70,-60}}, color={0,0,255}));
  connect(cyclingProxy.n, ground.p) annotation(Line(points={{50,-10},{50,-40},{-70,-40},{-70,-60}}, color={0,0,255}));
  voltage = supply.v;
  current = background.i + heater.i + cyclingProxy.i;
  pInstant = voltage * current;
  pTotal = pBase + pHeater + pCycle;
  annotation(uses(Modelica(version="4.1.0")),
    experiment(StartTime=0, StopTime=60, Interval=0.001, Tolerance=1e-6));
end ElemoniStarter;
