CREATE TABLE `portals2` (
  `Id` int(11) NOT NULL AUTO_INCREMENT,
  `ping` datetime DEFAULT NULL,
  `pong` datetime DEFAULT NULL,
  `name` varchar(50) NOT NULL,
  `status` tinyint(1) DEFAULT NULL,
  `image_url` varchar(160) DEFAULT NULL,
  `portal_url` varchar(80) DEFAULT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `ping_UNIQUE` (`ping`),
  UNIQUE KEY `pong_UNIQUE` (`pong`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;
