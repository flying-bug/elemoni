model ElemoniHouse "Illustrative Vietnam household: active-power signals, not wiring"
  parameter Boolean scheduledLoadsEnabled=true;
  parameter Real loadShiftHours=0 "Non-AC schedule phase; positive moves use earlier";
  parameter Modelica.Units.SI.Time kettleDurationSeconds=300 "Synthetic run duration, not boiling physics";
  parameter Modelica.Units.SI.Power Plights=54 "Six 9 W LEDs";
  parameter Modelica.Units.SI.Power Pfan=45;
  parameter Modelica.Units.SI.Power Ptv=80;
  parameter Modelica.Units.SI.Power Prouter=10;
  parameter Modelica.Units.SI.Power PriceCook=600;
  parameter Modelica.Units.SI.Power PriceWarm=40;
  parameter Modelica.Units.SI.Power Pkettle=1500;
  parameter Modelica.Units.SI.Power Pwash=400;
  parameter Modelica.Units.SI.Power Prinse=100;
  parameter Modelica.Units.SI.Power Pspin=300;
  parameter Modelica.Units.SI.Power Paircon=800 "Compressor electrical input, not cooling capacity";
  parameter Modelica.Units.SI.HeatCapacity roomCapacity=2e6;
  parameter Modelica.Units.SI.ThermalConductance roomConductance=120;
  parameter Modelica.Units.SI.Temperature roomInitial=303.15;
  parameter Modelica.Units.SI.Temperature roomLower=298.15 "25 C: stop compressor";
  parameter Modelica.Units.SI.Temperature roomUpper=299.15 "26 C: start compressor";
  parameter Modelica.Units.SI.Temperature outdoorMean=302.15 "29 C synthetic weather";
  parameter Modelica.Units.SI.TemperatureDifference outdoorAmplitude=4;
  parameter Real airconCOP=3;
  parameter Modelica.Units.SI.Power indoorFanPower=30;
  parameter Modelica.Units.SI.Power airconStandbyPower=2;
  parameter Modelica.Units.SI.HeatFlowRate solarPeak=350;
  parameter Modelica.Units.SI.HeatFlowRate occupantHeat=160;
  ElemoniFridge fridge(final Pbackground=0)
    annotation(Placement(transformation(origin={70,-80},extent={{-10,-10},{10,10}})));
  output Modelica.Units.SI.Power pFridge;
  output Modelica.Units.SI.Power pLights;
  output Modelica.Units.SI.Power pFan;
  output Modelica.Units.SI.Power pTV;
  output Modelica.Units.SI.Power pRouter;
  output Modelica.Units.SI.Power pRiceCooker;
  output Modelica.Units.SI.Power pKettle;
  output Modelica.Units.SI.Power pWasher;
  output Modelica.Units.SI.Power pAircon;
  output Modelica.Units.SI.Power pTotal;
  output Real cabinetC(unit="degC");
  output Real energyKWh(unit="kW.h",start=0,fixed=true);
  output Real energyOtherKWh(unit="kW.h",start=0,fixed=true);
  output Real energyAirconKWh(unit="kW.h",start=0,fixed=true);
  output Real roomCelsius(unit="degC");
  output Real outdoorCelsius(unit="degC");
  output Boolean airconAllowed;
  output Boolean airconCompressorOn;
  output Modelica.Units.SI.HeatFlowRate qRoomWall;
  output Modelica.Units.SI.HeatFlowRate qSolar;
  output Modelica.Units.SI.HeatFlowRate qOccupants;
  output Modelica.Units.SI.HeatFlowRate qIndoorFan;
  output Modelica.Units.SI.HeatFlowRate qAirconCooling;
  output Modelica.Units.SI.TemperatureSlope roomSlope;
  Modelica.Blocks.Sources.RealExpression refrigerator(y=pFridge)
    annotation(Placement(transformation(origin={-65,80},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression lights(y=pLights)
    annotation(Placement(transformation(origin={-65,60},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression fan(y=pFan)
    annotation(Placement(transformation(origin={-65,40},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression television(y=pTV)
    annotation(Placement(transformation(origin={-65,20},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression router(y=pRouter)
    annotation(Placement(transformation(origin={-65,0},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression riceCooker(y=pRiceCooker)
    annotation(Placement(transformation(origin={-65,-20},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression kettle(y=pKettle)
    annotation(Placement(transformation(origin={-65,-40},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression washer(y=pWasher)
    annotation(Placement(transformation(origin={-65,-60},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Sources.RealExpression aircon(y=pAircon)
    annotation(Placement(transformation(origin={-65,-80},extent={{-15,-8},{15,8}})));
  Modelica.Blocks.Math.MultiSum totalPower(nu=9)
    annotation(Placement(transformation(origin={35,0},extent={{-10,-10},{10,10}})));
protected
  Real hourOfDay;
  Real loadHour;
  Modelica.Units.SI.Temperature roomT(start=roomInitial,fixed=true);
  Modelica.Units.SI.Temperature outdoorT;
initial equation
  assert(kettleDurationSeconds >= 1 and kettleDurationSeconds <= 1800, "Invalid kettle duration");
  assert(loadShiftHours >= -3 and loadShiftHours <= 3, "Invalid load schedule shift");
  assert(roomCapacity > 0 and roomConductance > 0 and airconCOP > 0
    and roomLower > 0 and roomLower < roomUpper and roomInitial > 0
    and outdoorAmplitude >= 0 and outdoorMean-outdoorAmplitude > 0
    and indoorFanPower >= 0 and airconStandbyPower >= 0 and solarPeak >= 0 and occupantHeat >= 0,
    "Invalid room thermal configuration");
  assert(Plights >= 0 and Pfan >= 0 and Ptv >= 0 and Prouter >= 0
    and PriceCook >= 0 and PriceWarm >= 0 and Pkettle >= 0 and Pwash >= 0
    and Prinse >= 0 and Pspin >= 0 and Paircon >= 0,
    "Invalid household load power");
equation
  hourOfDay = mod(time/3600,24);
  loadHour = mod(hourOfDay+loadShiftHours,24);
  pFridge = fridge.pFridge;
  cabinetC = fridge.cabinetC;
  pLights = if scheduledLoadsEnabled and ((loadHour >= 5.5 and loadHour < 7)
    or (loadHour >= 18 and loadHour < 23)) then Plights else 0;
  pFan = if scheduledLoadsEnabled and ((loadHour >= 12 and loadHour < 14)
    or loadHour >= 18) then Pfan else 0;
  pTV = if scheduledLoadsEnabled and loadHour >= 19 and loadHour < 22 then Ptv else 0;
  pRouter = if scheduledLoadsEnabled then Prouter else 0;
  pRiceCooker = if not scheduledLoadsEnabled then 0
    elseif (loadHour >= 10.5 and loadHour < 11) or (loadHour >= 17.5 and loadHour < 18) then PriceCook
    elseif (loadHour >= 11 and loadHour < 12) or (loadHour >= 18 and loadHour < 19) then PriceWarm else 0;
  pKettle = if scheduledLoadsEnabled and ((loadHour >= 6.5 and loadHour < 6.5+kettleDurationSeconds/3600)
    or (loadHour >= 20 and loadHour < 20+kettleDurationSeconds/3600)) then Pkettle else 0;
  pWasher = if not scheduledLoadsEnabled then 0
    elseif loadHour >= 9 and loadHour < 9+1/3 then Pwash
    elseif loadHour >= 9+1/3 and loadHour < 9.5 then Prinse
    elseif loadHour >= 9.5 and loadHour < 9+2/3 then Pspin else 0;
  outdoorT = outdoorMean + outdoorAmplitude*sin(2*Modelica.Constants.pi*(hourOfDay/24-0.375));
  outdoorCelsius = outdoorT-273.15;
  roomCelsius = roomT-273.15;
  qRoomWall = roomConductance*(outdoorT-roomT);
  qSolar = if hourOfDay >= 6 and hourOfDay < 18 then
    solarPeak*max(0,sin(Modelica.Constants.pi*(hourOfDay-6)/12)) else 0;
  qOccupants = if hourOfDay < 6 or hourOfDay >= 22 then occupantHeat else 0;
  airconAllowed = scheduledLoadsEnabled and (hourOfDay < 6 or hourOfDay >= 22);
  when initial() then
    airconCompressorOn = airconAllowed and roomInitial >= roomUpper;
  elsewhen not airconAllowed then
    airconCompressorOn = false;
  elsewhen airconAllowed and roomT >= roomUpper then
    airconCompressorOn = true;
  elsewhen airconAllowed and roomT <= roomLower then
    airconCompressorOn = false;
  end when;
  qIndoorFan = if airconAllowed then indoorFanPower else 0;
  qAirconCooling = if airconCompressorOn then airconCOP*Paircon else 0;
  roomSlope = (qRoomWall+qSolar+qOccupants+qIndoorFan-qAirconCooling)/max(roomCapacity,1e-9);
  der(roomT) = roomSlope;
  pAircon = if not scheduledLoadsEnabled then 0 elseif airconAllowed then
    (if airconCompressorOn then Paircon else 0)+indoorFanPower else airconStandbyPower;
  connect(refrigerator.y,totalPower.u[1]) annotation(Line(points={{-48.5,80},{-30,80},{25, 0}},color={0,0,127}));
  connect(lights.y,totalPower.u[2]) annotation(Line(points={{-48.5,60},{-25,60},{25, 0}},color={0,0,127}));
  connect(fan.y,totalPower.u[3]) annotation(Line(points={{-48.5,40},{-20,40},{25, 0}},color={0,0,127}));
  connect(television.y,totalPower.u[4]) annotation(Line(points={{-48.5,20},{-15,20},{25, 0}},color={0,0,127}));
  connect(router.y,totalPower.u[5]) annotation(Line(points={{-48.5,0},{25, 0}},color={0,0,127}));
  connect(riceCooker.y,totalPower.u[6]) annotation(Line(points={{-48.5,-20},{-15,-20},{25, 0}},color={0,0,127}));
  connect(kettle.y,totalPower.u[7]) annotation(Line(points={{-48.5,-40},{-20,-40},{25, 0}},color={0,0,127}));
  connect(washer.y,totalPower.u[8]) annotation(Line(points={{-48.5,-60},{-25,-60},{25,0}},color={0,0,127}));
  connect(aircon.y,totalPower.u[9]) annotation(Line(points={{-48.5,-80},{-30,-80},{25, 0}},color={0,0,127}));
  pTotal = totalPower.y;
  der(energyKWh) = pTotal/3600000;
  der(energyOtherKWh) = (pLights+pFan+pTV+pRouter+pRiceCooker+pKettle+pWasher+pAircon)/3600000;
  der(energyAirconKWh) = pAircon/3600000;
  annotation(uses(Modelica(version="4.1.0")),
    experiment(StartTime=0,StopTime=86400,Interval=1,Tolerance=1e-7),
    Diagram(graphics={Text(extent={{-100,105},{100,92}},textString="Synthetic household - power signals (W), not electrical wires"),
      Text(extent={{45,12},{100,-12}},textString="pTotal (W)")}),
    Documentation(info="<html><p>Load ElemoniFridge.mo first. Illustrative Vietnam daily scenario, not a calibrated home. Refrigerator and air-conditioned room have thermal dynamics. Other loads use scheduled active-power envelopes. Conventional ON/OFF aircon, not inverter. Diagram lines are signals, not electrical wiring.</p></html>"));
end ElemoniHouse;
